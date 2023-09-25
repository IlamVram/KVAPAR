import traceback

from mainCode import DicomController

if __name__ == "__main__":
    try:
        dcim = DicomController()
        dcim.start_up()
    except Exception as ex:
        traceback.print_exc()

