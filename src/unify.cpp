#include "unify.hpp"

#include <algorithm>
#include <map>
#include <tuple>

namespace adi {
namespace unify {
namespace {

std::string dedupKey(const QsoRecord& record) {
    return toUpper(record.call()) + "\x1f" + record.band() + "\x1f" +
           trim(record.get("qso_date")) + "\x1f" + trim(record.get("time_on")) +
           "\x1f" + record.mode();
}

// Copy empty fields of duplicate `newRecord` into `base`.
void mergeRecord(QsoRecord& base, const QsoRecord& newRecord) {
    for (const auto& kv : newRecord.fields) {
        if (kv.second.empty()) continue;
        auto it = base.fields.find(kv.first);
        if (it == base.fields.end() || it->second.empty()) {
            base.fields[kv.first] = kv.second;
        }
    }
}

bool sortKeyLess(const QsoRecord& a, const QsoRecord& b) {
    return std::make_tuple(trim(a.get("qso_date")), trim(a.get("time_on")),
                           a.call(), a.band()) <
           std::make_tuple(trim(b.get("qso_date")), trim(b.get("time_on")),
                           b.call(), b.band());
}

}  // namespace

UnifyResult unifyRecords(const QsoRecordVec& records, bool dedupe, bool sort) {
    UnifyResult result;
    std::map<std::string, size_t> seen;
    for (const auto& record : records) {
        const std::string key = dedupKey(record);
        auto it = seen.find(key);
        if (dedupe && it != seen.end()) {
            mergeRecord(result.records[it->second], record);
            ++result.removed;
            continue;
        }
        if (dedupe) seen[key] = result.records.size();
        result.records.push_back(record);
    }
    if (sort) {
        std::stable_sort(result.records.begin(), result.records.end(),
                         sortKeyLess);
    }
    return result;
}

}  // namespace unify
}  // namespace adi
