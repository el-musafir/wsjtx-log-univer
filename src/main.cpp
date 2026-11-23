#include <QApplication.h>

#include "log_window.hpp"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    LogWindow window;
    window.show();
    return app.exec();
}
