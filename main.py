import sys
from PyQt6.QtWidgets import QApplication
from main_window import BudgetTrackerWindow


def main():
    # Catch any uncaught exceptions
    def exception_hook(exctype, value, tb):
        print("\n" + "="*60)
        print("UNCAUGHT EXCEPTION - APP CRASHED:")
        print("="*60)
        print(f"Type: {exctype.__name__}")
        print(f"Value: {value}")
        print("\nTraceback:")
        import traceback
        traceback.print_tb(tb)
        print("="*60)
    
    sys.excepthook = exception_hook
    
    try:
        app = QApplication(sys.argv)
        window = BudgetTrackerWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("\n" + "="*60)
        print("EXCEPTION IN MAIN:")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("="*60)


if __name__ == '__main__':
    main()