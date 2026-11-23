#ifndef WSJTX_LOG_WINDOW_HPP
#define WSJTX_LOG_WINDOW_HPP

#include <QMainWindow.h>
#include <QString.h>
#include <QStringList.h>
#include <vector>

#include "adi.hpp"

class QTableWidget;
class QTableWidgetItem;
class QLabel;
class QPushButton;
class QCheckBox;

// One row of the log list: a log file plus its state.
struct LogRow {
    QString path;
    bool sel = true;
    int count = -1;  // number of QSOs read; -1 = not read yet
    adi::QsoRecordVec records;
    QString error;
};

class LogWindow : public QMainWindow {
    Q_OBJECT

  public:
    explicit LogWindow(QWidget* parent = nullptr);

    // Data operations (mirror the Python GUI's data model).
    int addFiles(const QStringList& paths);
    int addDirectory(const QString& directory);
    bool toggle(const QString& path);
    void readLogs();
    QString saveUnified(const QString& path = QString());

    const std::vector<LogRow>& rows() const { return rows_; }

  private slots:
    void onAddFilesButton();
    void onAddDirectoryButton();
    void onReadLogsButton();
    void onSaveUnifiedButton();
    void onItemDoubleClicked(QTableWidgetItem* item);

  private:
    void syncTable();
    void toggleRow(int row);
    QString summary() const;
    void setStatus(const QString& text);

    QTableWidget* logTable_ = nullptr;
    QPushButton* addFilesButton_ = nullptr;
    QPushButton* addDirectoryButton_ = nullptr;
    QPushButton* readLogsButton_ = nullptr;
    QPushButton* saveUnifiedButton_ = nullptr;
    QPushButton* closeButton_ = nullptr;
    QCheckBox* dedupeCheck_ = nullptr;
    QCheckBox* sortCheck_ = nullptr;
    QLabel* statusLabel_ = nullptr;
    std::vector<LogRow> rows_;
};

#endif  // WSJTX_LOG_WINDOW_HPP
