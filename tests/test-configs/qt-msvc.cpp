#include <QCoreApplication>
#include <QDebug>

auto main(int argc, char *argv[]) -> int
{
    QCoreApplication app{argc, argv};
    qDebug() << "QtPresetCheck: Qt" << QT_VERSION_STR << "is working with" << qEnvironmentVariable("QTDIR");
    return 0;
}
