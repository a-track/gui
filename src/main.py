import sys
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont
from PyQt6.QtCore import Qt, QSettings
from main_window_tabbed import BudgetTrackerWindow
from startup_dialog import StartupDialog


def create_placeholder_splash():

    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor(255, 255, 255))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.fillRect(0, 0, 500, 300, QColor(245, 247, 250))
    painter.fillRect(0, 0, 500, 10, QColor(33, 150, 243))

    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(33, 150, 243))
    painter.drawText(pixmap.rect().adjusted(0, -20, 0, 0),
                     Qt.AlignmentFlag.AlignCenter, "Budget Tracker")

    font_sub = QFont("Segoe UI", 12)
    painter.setFont(font_sub)
    painter.setPen(QColor(100, 100, 100))
    painter.drawText(pixmap.rect().adjusted(0, 60, 0, 0),
                     Qt.AlignmentFlag.AlignCenter, "Loading your finances...")

    painter.end()
    return pixmap


def main():
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
        import ctypes
        myappid = 'antigravity.budgettracker.app.3.10'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("BudgetTracker")
    app.setOrganizationName("BudgetTools")
    app.setOrganizationDomain("budgettracker.local")

    while True:
        splash_pix = create_placeholder_splash()
        splash = QSplashScreen(splash_pix)
        splash.show()
        app.processEvents()

        settings = QSettings()
        db_path = settings.value("db_path", "")

        if not db_path or not os.path.exists(db_path):
            splash.close()

            dialog = StartupDialog()
            if dialog.exec():
                db_path = dialog.result_path
                settings.setValue("db_path", db_path)

                splash.show()
                app.processEvents()

                if getattr(dialog, 'mode', 'new') == 'sample':
                    try:
                        from import_export import DataManager
                        from models import BudgetApp

                        app_engine = BudgetApp(db_path)
                        app_engine.close()

                        dm = DataManager(db_path)
                        splash.showMessage(
                            "Generating sample data...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, QColor("black"))
                        app.processEvents()

                        success, msg = dm.load_sample_data()

                        if not success:
                            QMessageBox.warning(
                                None, "Sample Data Error", f"Could not load sample data: {msg}")

                    except Exception as e:
                        pass
            else:
                sys.exit(0)

        try:
            window = BudgetTrackerWindow(db_path)
            window.show()
            splash.finish(window)

            exit_code = app.exec()

            if window:
                window.close()
                try:
                    window.deleteLater()
                except:
                    pass
                del window

            if exit_code == 888:
                continue
            else:
                sys.exit(exit_code)

        except Exception as e:
            import traceback
            traceback.print_exc()
            try:

                error_msg = str(e)
                if "IO Error" in error_msg and "process cannot access the file" in error_msg:
                    error_msg = f"Database Locked!\n\nAnother instance of Budget Tracker seems to be running and holding the database lock.\n\nPlease close 'BudgetTracker_V3.5.exe' or other Python instances and try again.\n\nDetails: {e}"

                QMessageBox.critical(
                    None, "Application Error", f"Critical Error: {error_msg}")
            except:
                pass
            sys.exit(1)


if __name__ == '__main__':
    main()
