"""
Invoice OCR - Multi-module recognition system.
"""

from core.table_ocr import process_all as table_ocr_process_all


MENU = {
    "1": ("方框识别金额", table_ocr_process_all),
    # "2": ("xxx", xxx_process_all),
    # "3": ("xxxx", xxxx_process_all),
}


def main():
    print("=" * 40)
    print("  Invoice OCR")
    print("=" * 40)

    for key, (label, _) in MENU.items():
        print(f"  {key}. {label}")

    print("=" * 40)
    choice = input("Select: ").strip()

    if choice not in MENU:
        print(f"Invalid choice: {choice}")
        return

    label, handler = MENU[choice]
    print(f"\nRunning: {label}")
    handler()


if __name__ == "__main__":
    main()
