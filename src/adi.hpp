#ifndef WSJTX_ADI_HPP
#define WSJTX_ADI_HPP

#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace adi {

// String helpers used by the parser and the unifier.
std::string trim(const std::string& s);
std::string toUpper(const std::string& s);
std::string toLower(const std::string& s);

// One QSO record: a mapping of lowercase ADIF tag names to values.
struct QsoRecord {
    std::map<std::string, std::string> fields;

    std::string get(const std::string& key,
                    const std::string& fallback = std::string()) const;
    bool has(const std::string& key) const;

    // The other station's callsign ("" when absent).
    std::string call() const { return trim(get("call")); }

    // The effective operating mode ("FT8", "FT4", ...). WSJT-X writes FT4
    // as mode=MFSK + submode=FT4 and reports the submode as the mode here.
    std::string mode() const;

    // The band name upper-cased ("20m" -> "20M").
    std::string band() const { return toUpper(trim(get("band"))); }

    std::pair<std::string, std::string> dateTimeKey() const;
};

using QsoRecordVec = std::vector<QsoRecord>;

struct AdifParseError : std::runtime_error {
    explicit AdifParseError(const std::string& message)
        : std::runtime_error(message) {}
};

// Parse an ADIF log (WSJT-X / WS "wsjtx_log.adi" style) into records.
QsoRecordVec parseAdiText(const std::string& text);
QsoRecordVec parseAdiFile(const std::string& path);

// Render one record back to an ADIF string ending with "<eor>".
std::string renderRecord(const QsoRecord& record);

// Write records as a WSJT-X style ADIF log; returns false on I/O error.
bool writeAdi(const std::string& path, const QsoRecordVec& records);

}  // namespace adi

#endif  // WSJTX_ADI_HPP
