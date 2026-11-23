#include "adi.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <iterator>
#include <set>

namespace adi {

std::string trim(const std::string& s) {
    size_t begin = 0;
    size_t end = s.size();
    while (begin < end &&
           std::isspace(static_cast<unsigned char>(s[begin]))) {
        ++begin;
    }
    while (end > begin &&
           std::isspace(static_cast<unsigned char>(s[end - 1]))) {
        --end;
    }
    return s.substr(begin, end - begin);
}

std::string toUpper(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) {
                       return static_cast<char>(std::toupper(c));
                   });
    return out;
}

std::string toLower(const std::string& s) {
    std::string out = s;
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) {
                       return static_cast<char>(std::tolower(c));
                   });
    return out;
}

std::string QsoRecord::get(const std::string& key,
                           const std::string& fallback) const {
    auto it = fields.find(key);
    return it == fields.end() ? fallback : it->second;
}

bool QsoRecord::has(const std::string& key) const {
    return fields.find(key) != fields.end();
}

std::pair<std::string, std::string> QsoRecord::dateTimeKey() const {
    return std::make_pair(trim(get("qso_date")), trim(get("time_on")));
}

// Effective operating mode: WSJT-X writes FT4 as mode=MFSK with a
// submode=FT4 tag; the submode is reported as the mode in that case.
std::string QsoRecord::mode() const {
    std::string m = toUpper(trim(get("mode")));
    if (m.empty() || m == "MFSK") {
        std::string s = toUpper(trim(get("submode")));
        if (!s.empty()) m = s;
    }
    return m;
}

namespace {

bool isTerminator(const std::string& name) {
    static const std::set<std::string> kTerminators = {"eoh", "eor", "eof"};
    return kTerminators.count(name) != 0;
}

// Canonical field order used when writing records (mirrors the Python app).
const std::vector<std::string>& canonicalFields() {
    static const std::vector<std::string> kFields = {
        "call", "gridsquare", "mode", "submode", "rst_sent", "rst_rcvd",
        "qso_date", "time_on", "qso_date_off", "time_off", "band", "freq",
        "station_callsign", "my_gridsquare",
    };
    return kFields;
}

const std::set<std::string>& canonicalSet() {
    static const std::set<std::string> kSet(canonicalFields().begin(),
                                            canonicalFields().end());
    return kSet;
}

std::string formatTag(const std::string& name, const std::string& value) {
    return "<" + name + ":" + std::to_string(value.size()) + ">" + value;
}

std::string normalizeNewlines(const std::string& text) {
    std::string out;
    out.reserve(text.size());
    for (size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '\r') {
            if (i + 1 < text.size() && text[i + 1] == '\n') ++i;
            out += '\n';
        } else {
            out += text[i];
        }
    }
    return out;
}

// Parses one tag at *pos. On success, fills name/value and advances *pos
// past the tag; returns true. On failure, returns false and advances *pos
// past the '<' so the caller can continue scanning.
bool scanTag(const std::string& text, size_t* pos, std::string* name,
             std::string* value) {
    const size_t n = text.size();
    const size_t start = text.find('<', *pos);
    if (start == std::string::npos) {
        *pos = n;
        return false;
    }
    const size_t i = start + 1;
    if (i >= n || !(std::isalpha(static_cast<unsigned char>(text[i])) ||
                    text[i] == '_')) {
        *pos = i;
        return false;
    }
    size_t p = i;
    while (p < n &&
           (std::isalnum(static_cast<unsigned char>(text[p])) ||
            text[p] == '_')) {
        ++p;
    }
    *name = toLower(text.substr(i, p - i));
    std::string lengthStr;
    if (p < n && text[p] == ':') {
        size_t d = p + 1;
        while (d < n && std::isdigit(static_cast<unsigned char>(text[d]))) {
            ++d;
        }
        if (d > p + 1 && d < n && text[d] == '>') {
            lengthStr = text.substr(p + 1, d - (p + 1));
            p = d;
        }
    }
    if (p >= n || text[p] != '>') {
        *pos = start + 1;
        return false;
    }
    ++p;  // past '>'
    if (!lengthStr.empty()) {
        long length = 0;
        try {
            length = std::stol(lengthStr);
        } catch (const std::exception&) {
            length = 0;
        }
        if (length < 0) length = 0;
        const size_t valueBegin = p;
        *value = text.substr(valueBegin, static_cast<size_t>(length));
        p = valueBegin + value->size();
    } else {
        const size_t next = text.find('<', p);
        if (next == std::string::npos) {
            *value = text.substr(p);
            p = n;
        } else {
            *value = text.substr(p, next - p);
            p = next;
        }
    }
    *pos = p;
    return true;
}

}  // namespace

QsoRecordVec parseAdiText(const std::string& text) {
    QsoRecordVec records;
    QsoRecord current;
    bool haveCurrent = false;
    std::string name;
    std::string value;
    size_t pos = 0;
    while (pos < text.size()) {
        if (!scanTag(text, &pos, &name, &value)) continue;
        if (isTerminator(name)) {
            if (haveCurrent) {
                if (!current.call().empty()) records.push_back(current);
                current = QsoRecord();
                haveCurrent = false;
            }
            continue;
        }
        if (!haveCurrent) {
            current = QsoRecord();
            haveCurrent = true;
        }
        if (current.fields.find(name) == current.fields.end()) {
            current.fields[name] = value;
        }
    }
    if (haveCurrent && !current.call().empty()) records.push_back(current);
    return records;
}

QsoRecordVec parseAdiFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in.is_open()) {
        throw AdifParseError(path + ": cannot open file");
    }
    const std::string text((std::istreambuf_iterator<char>(in)),
                           std::istreambuf_iterator<char>());
    return parseAdiText(normalizeNewlines(text));
}

std::string renderRecord(const QsoRecord& record) {
    std::vector<std::string> parts;
    for (const std::string& name : canonicalFields()) {
        std::string value;
        if (name == "mode") {
            value = record.mode();
        } else {
            value = record.get(name);
        }
        if (!value.empty()) parts.push_back(formatTag(name, value));
    }
    for (const auto& kv : record.fields) {
        if (canonicalSet().count(kv.first) != 0 || kv.second.empty()) continue;
        parts.push_back(formatTag(kv.first, kv.second));
    }
    parts.push_back("<eor>");
    std::string out;
    for (size_t i = 0; i < parts.size(); ++i) {
        if (i > 0) out += " ";
        out += parts[i];
    }
    return out;
}

bool writeAdi(const std::string& path, const QsoRecordVec& records) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out.is_open()) return false;
    out << "ADIF Export\n<eoh>\n";
    for (const auto& record : records) out << renderRecord(record) << "\n";
    out.flush();
    return out.good();
}

}  // namespace adi
