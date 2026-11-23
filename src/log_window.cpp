#include "log_window.hpp"

#include <QAbstractItemView.h>
#include <QCheckBox.h>
#include <QDir.h>
#include <QDirIterator.h>
#include <QFileDialog.h>
#include <QFileInfo.h>
#include <QHBoxLayout.h>
#include <QHeaderView.h>
#include <QLabel.h>
#include <QMessageBox.h>
#include <QPushButton.h>
#include <QString.h>
#include <QTableWidget.h>
#include <QTableWidgetItem.h>
#include <QVBoxLayout.h>
#include <QWidget.h>

#include "adi.hpp"
#include "unify.hpp"

LogWindow::LogWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle("WSJTX Log Unifier");
    setMinimumSize(760, 540);

    QWidget* central = new QWidget(this);
    setCentralWidget(central);
    QVBoxLayout* layout = new QVBoxLayout(central);

    layout->addWidget(new QLabel(
        "Logs to take and unify (double-click a row to toggle):"), 0);

    logTable_ = new QTableWidget(central);
    logTable_->setColumnCount(3);
    {
        QStringList headers;
        headers.append("Take");
        headers.append("Log file");
        headers.append("QSOs read");
        logTable_->setHorizontalHeaderLabels(headers);
    }
    logTable_->horizontalHeader()->setSectionResizeMode(
        0, QHeaderView::ResizeToContents);
    logTable_->horizontalHeader()->setSectionResizeMode(
        1, QHeaderView::Stretch);
    logTable_->horizontalHeader()->setSectionResizeMode(
        2, QHeaderView::ResizeToContents);
    logTable_->setEditTriggers(QAbstractItemView::NoEditTriggers);
    layout->addWidget(logTable_, 1);

    QHBoxLayout* buttonsLayout = new QHBoxLayout();
    addFilesButton_ = new QPushButton("Add files...");
    addDirectoryButton_ = new QPushButton("Add directory...");
    readLogsButton_ = new QPushButton("Read logs");
    saveUnifiedButton_ = new QPushButton("Save unified log...");
    closeButton_ = new QPushButton("Close");
    buttonsLayout->addWidget(addFilesButton_);
    buttonsLayout->addWidget(addDirectoryButton_);
    buttonsLayout->addWidget(readLogsButton_);
    buttonsLayout->addWidget(saveUnifiedButton_);
    buttonsLayout->addWidget(closeButton_);
    layout->addLayout(buttonsLayout);

    QHBoxLayout* optionsLayout = new QHBoxLayout();
    dedupeCheck_ = new QCheckBox("Remove duplicate QSOs (call, band, time)");
    dedupeCheck_->setChecked(true);
    sortCheck_ = new QCheckBox("Sort QSOs by date/time");
    sortCheck_->setChecked(true);
    optionsLayout->addWidget(dedupeCheck_);
    optionsLayout->addWidget(sortCheck_);
    layout->addLayout(optionsLayout);

    statusLabel_ = new QLabel();
    layout->addWidget(statusLabel_, 0);
    setStatus("Add logs, read them, then save the unified log.");

    connect(addFilesButton_, &QPushButton::clicked, this,
            &LogWindow::onAddFilesButton);
    connect(addDirectoryButton_, &QPushButton::clicked, this,
            &LogWindow::onAddDirectoryButton);
    connect(readLogsButton_, &QPushButton::clicked, this,
            &LogWindow::onReadLogsButton);
    connect(saveUnifiedButton_, &QPushButton::clicked, this,
            &LogWindow::onSaveUnifiedButton);
    connect(closeButton_, &QPushButton::clicked, this, &QWidget::close);
    connect(logTable_, &QTableWidget::itemDoubleClicked, this,
            &LogWindow::onItemDoubleClicked);
}

int LogWindow::addFiles(const QStringList& paths) {
    int added = 0;
    for (const QString& path : paths) {
        bool known = false;
        for (const LogRow& row : rows_) {
            if (row.path == path) {
                known = true;
                break;
            }
        }
        if (known) continue;
        LogRow row;
        row.path = path;
        row.sel = true;
        row.count = -1;
        rows_.push_back(row);
        ++added;
    }
    syncTable();
    setStatus(summary());
    return added;
}

int LogWindow::addDirectory(const QString& directory) {
    if (directory.isEmpty()) return 0;
    QStringList logs;
    QDirIterator it(directory, QDirIterator::Subdirectories);
    while (it.hasNext()) {
        const QString file = QDir::toNativeSeparators(it.next());
        if (QFileInfo(file).isFile() &&
            file.toLower().endsWith(QString(".adi"))) {
            logs.append(file);
        }
    }
    logs.sort();
    return addFiles(logs);
}

bool LogWindow::toggle(const QString& path) {
    for (size_t i = 0; i < rows_.size(); ++i) {
        if (rows_[i].path == path) {
            toggleRow(static_cast<int>(i));
            return rows_[i].sel;
        }
    }
    return false;
}

void LogWindow::toggleRow(int row) {
    if (row < 0 || row >= static_cast<int>(rows_.size())) return;
    rows_[row].sel = !rows_[row].sel;
    syncTable();
}

void LogWindow::readLogs() {
    for (LogRow& row : rows_) {
        try {
            row.records = adi::parseAdiFile(row.path.toStdString());
            row.count = static_cast<int>(row.records.size());
            row.error.clear();
        } catch (const adi::AdifParseError& e) {
            row.records.clear();
            row.count = -1;
            row.error = QString(e.what());
        }
    }
    syncTable();
    setStatus(summary());
}

QString LogWindow::saveUnified(const QString& path) {
    readLogs();
    adi::QsoRecordVec records;
    QStringList bad;
    int selected = 0;
    for (const LogRow& row : rows_) {
        if (!row.sel) continue;
        ++selected;
        if (!row.error.isEmpty()) {
            bad.append(row.path);
            continue;
        }
        for (const adi::QsoRecord& rec : row.records) records.push_back(rec);
    }
    if (selected == 0) {
        QMessageBox::warning(
            this, "Nothing to do",
            QString("No log is selected. Add logs and keep them selected."));
        return QString();
    }
    if (!bad.isEmpty()) {
        QMessageBox::warning(this, "Skipped unreadable logs",
                             QString("Could not read:\n") + bad.join("\n"));
    }
    if (records.isEmpty()) return QString();

    QString outPath = path;
    if (outPath.isEmpty()) {
        outPath = QFileDialog::getSaveFileName(
            this, "Save the unified log",
            QDir::home().filePath("unified_log.adi"),
            "ADIF (*.adi);;All files (*)");
        if (outPath.isEmpty()) return QString();
    }

    adi::unify::UnifyResult result = adi::unify::unifyRecords(
        records, dedupeCheck_->isChecked(), sortCheck_->isChecked());
    if (!adi::writeAdi(outPath.toStdString(), result.records)) {
        QMessageBox::critical(this, "Error",
                              QString("Could not write ") + outPath);
        return QString();
    }

    QString note;
    if (result.removed > 0) {
        note = QString(" (%1 duplicates removed)").arg(result.removed);
    }
    setStatus(QString("Wrote ") +
              QString::number(static_cast<int>(result.records.size())) +
              QString(" QSOs to ") + outPath + note);
    QMessageBox::information(
        this, "Saved",
        QString("Wrote ") +
            QString::number(static_cast<int>(result.records.size())) +
            QString(" QSOs to ") + outPath + note);
    return outPath;
}

QString LogWindow::summary() const {
    int total = 0;
    int selected = 0;
    for (const LogRow& row : rows_) {
        const int count = row.count > 0 ? row.count : 0;
        total += count;
        if (row.sel) selected += count;
    }
    return QString("%1 logs - %2 selected QSOs - %3 QSOs read in total")
        .arg(static_cast<int>(rows_.size()))
        .arg(selected)
        .arg(total);
}

void LogWindow::setStatus(const QString& text) {
    if (statusLabel_) statusLabel_->setText(text);
}

void LogWindow::syncTable() {
    logTable_->setRowCount(static_cast<int>(rows_.size()));
    for (int i = 0; i < static_cast<int>(rows_.size()); ++i) {
        const LogRow& row = rows_[i];
        QTableWidgetItem* take = new QTableWidgetItem;
        take->setFlags(take->flags() | Qt::ItemIsUserCheckable);
        take->setCheckState(row.sel ? Qt::Checked : Qt::Unchecked);
        logTable_->setItem(i, 0, take);
        logTable_->setItem(i, 1, new QTableWidgetItem(row.path));
        logTable_->setItem(i, 2, new QTableWidgetItem(
            row.count < 0 ? QString(QChar(0x2014))
                          : QString::number(row.count)));
    }
}

void LogWindow::onAddFilesButton() {
    QStringList files = QFileDialog::getOpenFileNames(
        this, "Select WSJT-X / WS logs", QDir::home().absolutePath(),
        "ADIF (*.adi);;WSJT-X / WS log (wsjtx_log.adi);;All files");
    addFiles(files);
}

void LogWindow::onAddDirectoryButton() {
    addDirectory(QFileDialog::getExistingDirectory(
        this, "Select the log directory", QDir::home().absolutePath()));
}

void LogWindow::onReadLogsButton() { readLogs(); }

void LogWindow::onSaveUnifiedButton() { saveUnified(QString()); }

void LogWindow::onItemDoubleClicked(QTableWidgetItem* item) {
    if (item) toggleRow(item->row());
}
