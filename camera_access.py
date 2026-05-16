import argparse
import platform
import sys
import time

try:
    import cv2
except ImportError:
    sys.exit("Error: OpenCV is required. Install it with 'pip install opencv-python'.")


def is_raspberry_pi_4() -> bool:
    if platform.system() != "Linux":
        return False

    try:
        with open("/proc/device-tree/model", "r", encoding="utf-8") as model_file:
            model = model_file.read().strip()
            if "Raspberry Pi 4" in model:
                return True
    except Exception:
        pass

    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as cpuinfo_file:
            cpuinfo = cpuinfo_file.read().lower()
            if "raspberry pi 4" in cpuinfo or "raspberry pi" in cpuinfo and "bcm2711" in cpuinfo:
                return True
    except Exception:
        pass

    return False


def open_camera(source: str, device_index: int, stream_url: str) -> cv2.VideoCapture:
    if source == "usb":
        return cv2.VideoCapture(device_index, cv2.CAP_ANY)

    if source == "ip":
        if not stream_url:
            raise ValueError("IP camera source requires --url.")
        return cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)

    if source == "picamera":
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not cap.isOpened():
            raise RuntimeError("Could not open Raspberry Pi Camera Module on /dev/video0. Ensure libcamera and v4l2loopback are configured.")
        return cap

    raise ValueError(f"Unsupported camera source: {source}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raspberry Pi 4 camera access utility")
    parser.add_argument(
        "--source",
        choices=["usb", "ip", "picamera"],
        default="usb",
        help="Camera source type: usb for local USB camera, ip for wireless stream, picamera for Raspberry Pi Camera Module",
    )
    parser.add_argument("--index", type=int, default=0, help="USB camera device index (default: 0)")
    parser.add_argument("--url", type=str, default="", help="RTSP/HTTP URL for IP camera streams")
    parser.add_argument("--width", type=int, default=640, help="Frame width")
    parser.add_argument("--height", type=int, default=480, help="Frame height")
    parser.add_argument("--display", action="store_true", help="Display video in a window")
    parser.add_argument("--output", type=str, default="", help="Save output frames to an AVI file")
    parser.add_argument("--duration", type=int, default=30, help="Recording duration in seconds")
    return parser.parse_args()


def main() -> None:
    if not is_raspberry_pi_4():
        sys.exit("This script can only run on Raspberry Pi 4.")

    args = parse_args()

    try:
        cap = open_camera(args.source, args.index, args.url)
    except Exception as exc:
        sys.exit(f"Camera open failed: {exc}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(args.output, fourcc, 20.0, (args.width, args.height))

    start_time = time.time()
    print(f"Streaming from source={args.source} for up to {args.duration} seconds...")

    while time.time() - start_time < args.duration:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Warning: frame read failed. Retrying...")
            time.sleep(0.2)
            continue

        if args.output and writer is not None:
            writer.write(frame)

        if args.display:
            cv2.imshow("Pi Camera Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("Stopping on user request.")
                break

    cap.release()
    if writer is not None:
        writer.release()
    if args.display:
        cv2.destroyAllWindows()

    print("Camera capture stopped.")


if __name__ == "__main__":
    main()
