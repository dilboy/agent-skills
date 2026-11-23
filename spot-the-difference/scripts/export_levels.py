"""Measure spot-the-difference answers and export verified image pairs locally."""

import argparse
import csv
import json
import math
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image


EXTENSIONS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}
OVERVIEW = ['关卡', '原图', '差异图', '宽', '高', '难度', '评分', '差异数', '遮罩']
DETAIL = ['点号', '改动类型', '来源', '模型', '框左', '框顶', '框宽', '框高',
          '命中 x', '命中 y', '归一化框左', '归一化框顶', '归一化框宽', '归一化框高',
          '归一化命中 x', '归一化命中 y', '变化像素数', '平均像素差']


def read_rgb(path):
    with Image.open(path) as image:
        if image.format not in EXTENSIONS:
            raise ValueError(f'Unsupported image format: {path.name}')
        if image.getexif().get(274, 1) != 1:
            raise ValueError(f'Normalize EXIF orientation before export: {path.name}')
        if getattr(image, 'is_animated', False):
            raise ValueError(f'Use a still image: {path.name}')
        if ('A' in image.getbands() or 'transparency' in image.info) and image.convert('RGBA').getchannel('A').getextrema()[0] != 255:
            raise ValueError(f'Flatten transparency before export: {path.name}')
        return np.asarray(image.convert('RGB'), dtype=np.int16), EXTENSIONS[image.format]


def measure(before, after, regions):
    if before.shape != after.shape:
        raise ValueError('Original and modified images must have identical dimensions')
    height, width = before.shape[:2]
    delta = np.max(np.abs(before-after), axis=2)
    mask = np.zeros((height, width), dtype=np.uint8)
    occupied = np.zeros_like(mask, dtype=bool)
    dimensions = np.array([width, height, width, height])
    answers = []
    for index, region in enumerate(regions, 1):
        box = region['box']
        if len(box) != 4 or any(type(value) is not int for value in box):
            raise ValueError(f'Answer {index} requires four integer bounds')
        x, y, right, bottom = box
        if not (0 <= x < right <= width and 0 <= y < bottom <= height):
            raise ValueError(f'Answer {index} is outside the image')
        area = np.s_[y:bottom, x:right]
        if occupied[area].any():
            raise ValueError(f'Answer {index} overlaps an earlier edit region')
        occupied[area] = True
        local = delta[area]
        changed = local > 0
        ys, xs = np.nonzero(changed)
        if len(xs) < max(10, width * height * .00008) or local[changed].mean() < 12:
            raise ValueError(f'Answer {index} does not contain a visible difference')
        mask[area][changed] = index
        nearest = np.argmin((xs-xs.mean())**2 + (ys-ys.mean())**2)
        point = [x + int(xs[nearest]), y + int(ys[nearest])]
        bounds = [x + int(xs.min()), y + int(ys.min()), int(np.ptp(xs))+1, int(np.ptp(ys))+1]
        answers.append({'id':index, 'kind':region['kind'], 'source':region['source'], 'model':region.get('model'),
                        'editBox':box, 'bbox':bounds, 'bboxNormalized':(np.array(bounds)/dimensions).tolist(),
                        'point':point, 'pointNormalized':[(point[0]+.5)/width,(point[1]+.5)/height],
                        'changedPixels':len(xs), 'meanRgbDelta':round(float(local[changed].mean()),1)})
    if np.any((delta > 0) & ~occupied):
        raise ValueError('Modified pixels were found outside the declared edit regions')
    return answers, mask


def export_level(spec, root, output):
    identifier = spec['id']
    regions = spec['regions']
    count = spec.get('count', len(regions))
    if type(count) is not int or not 1 <= count <= 255 or count != len(regions):
        raise ValueError('count must match the 1–255 declared regions')
    original = root / spec['original']
    modified = root / spec['modified']
    before, original_ext = read_rgb(original)
    after, modified_ext = read_rgb(modified)
    answers, mask = measure(before, after, regions)
    if 'delivery' in spec:
        modified = root / spec['delivery']
        delivery, modified_ext = read_rgb(modified)
        if (delivery.shape != after.shape or modified_ext != '.jpg'
                or np.percentile(np.max(np.abs(delivery-after), axis=2), 99) > 12):
            raise ValueError('The delivery JPEG does not match the lossless modified image')
    names = {'original': f'{identifier}_a{original_ext}', 'modified': f'{identifier}_b{modified_ext}',
             'mask': f'masks/{identifier}_mask.png'}
    shutil.copyfile(original, output / names['original'])
    shutil.copyfile(modified, output / names['modified'])
    Image.fromarray(mask).save(output / names['mask'])
    score = spec.get('score')
    if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100):
        raise ValueError('An optional score must be a number between 0 and 100')
    return {'id':identifier, **names, 'width':before.shape[1], 'height':before.shape[0],
            'difficulty':spec.get('difficulty'), 'score':score, 'count':count, 'answers':answers}


def write_tables(folder, levels):
    def safe_row(values):
        return ["'"+value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@'))
                else value for value in values]

    fields = ('id','original','modified','width','height','difficulty','score','count','mask')
    with ((folder/'关卡总表.csv').open('w',encoding='utf-8-sig',newline='') as overview,
          (folder/'差异信息表.csv').open('w',encoding='utf-8-sig',newline='') as details):
        rows, differences = csv.writer(overview), csv.writer(details)
        rows.writerow(OVERVIEW)
        differences.writerow(OVERVIEW+DETAIL)
        for level in levels:
            summary = [level[field] for field in fields]
            rows.writerow(safe_row(summary))
            for answer in level['answers']:
                differences.writerow(safe_row(summary + [answer['id'],answer['kind'],answer['source'],answer['model'],
                    *answer['bbox'],*answer['point'],*answer['bboxNormalized'],*answer['pointNormalized'],
                    answer['changedPixels'],answer['meanRgbDelta']]))


def run(manifest, destination, progression):
    specs = json.loads(manifest.read_text(encoding='utf-8-sig'))['levels']
    if not isinstance(specs, list) or not specs:
        raise ValueError('The manifest needs a nonempty levels array')
    ids = [item['id'] for item in specs]
    if any(not isinstance(item,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',item) for item in ids):
        raise ValueError('Level IDs must be 1–64 characters using letters, digits, _ or -')
    if len({item.casefold() for item in ids}) != len(ids):
        raise ValueError('Level IDs must be unique')
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'Output already exists: {destination}')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.difference-',dir=destination.parent) as temp:
        staged = Path(temp)/'release'
        (staged/'masks').mkdir(parents=True)
        levels = []
        for spec in specs:
            try:
                levels.append(export_level(spec,manifest.parent,staged))
            except (ValueError,OSError,TypeError,KeyError) as error:
                raise ValueError(f"{spec['id']}: {error}") from error
        if progression:
            scores = [item['score'] for item in levels if item['score'] is not None]
            counts = [item['count'] for item in levels]
            if scores != sorted(scores) or counts != sorted(counts):
                raise ValueError('Supplied difficulty scores and difference counts must not decrease')
        write_tables(staged,levels)
        total = sum(item['count'] for item in levels)
        report = {'schemaVersion':1, 'levelCount':len(levels), 'answerCount':total, 'coordinateOrigin':'top-left',
                  'bboxFormat':['x','y','width','height'], 'editBoxFormat':['left','top','rightExclusive','bottomExclusive'],
                  'levels':levels}
        (staged/'关卡与差异.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'Output appeared during export: {destination}')
        staged.rename(destination)
    return len(levels),total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--check-progression',action='store_true')
    args = parser.parse_args()
    try:
        n, total = run(args.manifest,args.output,args.check_progression)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,f'{error}\n')
    print(f'Exported {n} levels and {total} answer points.')
