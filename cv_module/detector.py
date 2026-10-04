"""
وحدة الرؤية الحاسوبية لمشروع ParkMind.

تعمل هذه الوحدة كعملية مستقلة عن خادم Flask، وتتصل به فقط عبر طلبات HTTP.
لا تُستخدم بيئة افتراضية (venv) لتشغيلها، بل تُثبَّت التبعيات مباشرة عبر:
    pip install -r requirements.txt
ثم تُشغَّل الوحدة عبر:
    python cv_module/detector.py
"""

import json
import os
import time
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / 'spaces_config.json'
API_BASE_URL = os.environ.get('CV_API_BASE_URL', 'http://127.0.0.1:5000')
CV_INTERNAL_TOKEN = os.environ.get('CV_INTERNAL_TOKEN')
VIDEO_SOURCE = os.environ.get('CV_VIDEO_SOURCE', '0')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as config_file:
        return json.load(config_file)


def resolve_space_ids(lot_name, space_numbers):
    response = requests.get(f'{API_BASE_URL}/api/parking-lots', timeout=5)
    response.raise_for_status()
    lots = response.json()

    target_lot = next((lot for lot in lots if lot['name'] == lot_name), None)
    if target_lot is None:
        raise RuntimeError('لم يتم العثور على الموقف المحدد في ملف الإعداد داخل قاعدة البيانات')

    response = requests.get(f'{API_BASE_URL}/api/parking-lots/{target_lot["id"]}/spaces', timeout=5)
    response.raise_for_status()
    spaces = response.json()

    mapping = {}
    for space_number in space_numbers:
        match = next((space for space in spaces if space['space_number'] == space_number), None)
        if match is None:
            raise RuntimeError(f'مكان الوقوف {space_number} غير موجود في قاعدة البيانات')
        mapping[space_number] = match['id']
    return mapping


def preprocess_frame(frame, config):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    kernel_size = config['gaussian_blur_kernel']
    blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 1)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        config['adaptive_threshold_block_size'],
        config['adaptive_threshold_constant']
    )
    return binary


def classify_space(binary_frame, space, threshold):
    x, y, w, h = space['x'], space['y'], space['w'], space['h']
    roi = binary_frame[y:y + h, x:x + w]
    white_pixel_count = cv2.countNonZero(roi)
    return 'occupied' if white_pixel_count > threshold else 'vacant'


def push_status_update(space_id, new_status):
    try:
        response = requests.post(
            f'{API_BASE_URL}/api/parking-spaces/{space_id}/status',
            json={'status': new_status},
            headers={'X-CV-Token': CV_INTERNAL_TOKEN},
            timeout=5
        )
        if response.status_code != 200:
            print(f'تعذر تحديث حالة المكان رقم {space_id}: استجابة غير متوقعة من الخادم')
    except requests.RequestException:
        print(f'تعذر الاتصال بالخادم لتحديث حالة المكان رقم {space_id}')


def run():
    if not CV_INTERNAL_TOKEN:
        raise RuntimeError('يجب تعيين CV_INTERNAL_TOKEN داخل ملف .env قبل تشغيل وحدة الرؤية الحاسوبية')

    config = load_config()
    space_numbers = [space['space_number'] for space in config['spaces']]
    space_id_by_number = resolve_space_ids(config['lot_name'], space_numbers)

    video_source = int(VIDEO_SOURCE) if VIDEO_SOURCE.isdigit() else VIDEO_SOURCE
    capture = cv2.VideoCapture(video_source)
    if not capture.isOpened():
        raise RuntimeError('تعذر فتح مصدر الفيديو، تأكد من قيمة CV_VIDEO_SOURCE في ملف .env')

    smoothing_frames_required = config['temporal_smoothing_frames']
    threshold = config['occupancy_pixel_threshold']

    committed_status = {number: 'vacant' for number in space_numbers}
    pending_status = {number: None for number in space_numbers}
    pending_count = {number: 0 for number in space_numbers}

    print('بدأت وحدة الرؤية الحاسوبية بمراقبة الموقف:', config['lot_name'])

    try:
        while True:
            success, frame = capture.read()
            if not success:
                break

            binary_frame = preprocess_frame(frame, config)

            for space in config['spaces']:
                number = space['space_number']
                tentative_status = classify_space(binary_frame, space, threshold)

                if tentative_status == pending_status[number]:
                    pending_count[number] += 1
                else:
                    pending_status[number] = tentative_status
                    pending_count[number] = 1

                if (
                    pending_count[number] >= smoothing_frames_required
                    and tentative_status != committed_status[number]
                ):
                    committed_status[number] = tentative_status
                    push_status_update(space_id_by_number[number], tentative_status)

            time.sleep(0.1)
    except KeyboardInterrupt:
        print('تم إيقاف وحدة الرؤية الحاسوبية بواسطة المستخدم')
    finally:
        capture.release()


if __name__ == '__main__':
    run()
