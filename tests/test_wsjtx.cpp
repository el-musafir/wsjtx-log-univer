#include "adi.hpp"
#include "unify.hpp"

#include <filesystem>
#include <iostream>
#include <string>

using namespace adi;

namespace {

int failures = 0;

void check(bool condition, const char* what, int line) {
    if (!condition) {
        std::cerr << "FAIL (line " << line << "): " << what << std::endl;
        ++failures;
    }
}

#define CHECK(cond) check((cond), #cond, __LINE__)

QsoRecord makeRecord(const std::string& call, const std::string& date,
                     const std::string& time, const std::string& band) {
    QsoRecord r;
    r.fields["call"] = call;
    r.fields["qso_date"] = date;
    r.fields["time_on"] = time;
    r.fields["band"] = band;
    r.fields["mode"] = "FT8";
    return r;
}

}  // namespace

int main() {
    // Parse the sample log written by WSJT-X 2.7.0 (tests/fixtures).
    QsoRecordVec records;
    try {
        records = parseAdiFile(WSJTX_FIXTURE);
    } catch (const std::exception& e) {
        std::cerr << "could not read fixture: " << e.what() << std::endl;
        return 1;
    }
    CHECK(records.size() >= 20);
    CHECK(records[0].call() == "JA7DXX");
    CHECK(records[0].mode() == "FT8");
    CHECK(records[0].get("qso_date") == "20250504");
    CHECK(records[0].get("time_on") == "194945");
    CHECK(records[0].band() == "20M");
    CHECK(records[0].get("freq") == "14.074849");
    CHECK(records[0].get("station_callsign") == "DF3TN");
    CHECK(records[0].get("my_gridsquare") == "JN49");
    CHECK(records[0].get("gridsquare").empty());
    CHECK(records[0].get("time_off") == "194945");

    bool sawFt4 = false;
    for (const auto& r : records) {
        if (r.mode() == "FT4") {
            sawFt4 = true;
            CHECK(r.get("mode") == "MFSK");
            CHECK(r.get("submode") == "FT4");
        }
    }
    CHECK(sawFt4);

    bool sawCompound = false;
    for (const auto& r : records) {
        if (r.call().find('/') != std::string::npos) sawCompound = true;
    }
    CHECK(sawCompound);

    // Unify: the sample log has one duplicated ER0ITU record.
    const unify::UnifyResult unified = unify::unifyRecords(records);
    CHECK(unified.removed >= 1);
    CHECK(unified.records.size() ==
          records.size() - static_cast<size_t>(unified.removed));

    // Round trip: write then re-parse.
    const std::filesystem::path tmp =
        std::filesystem::temp_directory_path() / "wsjtx_unify_roundtrip.adi";
    CHECK(writeAdi(tmp.string(), records));
    const QsoRecordVec back = parseAdiFile(tmp.string());
    CHECK(back.size() == records.size());
    if (!records.empty() && !back.empty()) {
        CHECK(back[0].call() == records[0].call());
        CHECK(back[0].mode() == records[0].mode());
        CHECK(back[0].get("qso_date") == records[0].get("qso_date"));
        CHECK(back[0].get("time_on") == records[0].get("time_on"));
    }
    std::filesystem::remove(tmp);

    // Dedup and sort.
    const QsoRecord a = makeRecord("BV1EK", "20250511", "211430", "20M");
    const QsoRecord b = makeRecord("BV1EK", "20250511", "211430", "20M");
    const QsoRecord c = makeRecord("AA1A", "20250504", "000001", "15M");
    QsoRecordVec dupes{a, b, c};
    const unify::UnifyResult d = unify::unifyRecords(dupes, true, false);
    CHECK(d.removed == 1);
    CHECK(d.records.size() == 2);

    QsoRecordVec unsorted;
    unsorted.push_back(a);
    const QsoRecord later = makeRecord("JA7DXX", "20250504", "194945", "20M");
    unsorted.push_back(later);
    const unify::UnifyResult s = unify::unifyRecords(unsorted, false, true);
    CHECK(s.records[0].call() == "JA7DXX");
    CHECK(s.records[1].call() == "BV1EK");

    // Merge fills missing fields from duplicates.
    QsoRecord base = makeRecord("JA7DXX", "20250504", "194945", "20M");
    QsoRecord dupe = makeRecord("JA7DXX", "20250504", "194945", "20M");
    dupe.fields["time_off"] = "194945";
    const unify::UnifyResult m =
        unify::unifyRecords(QsoRecordVec{base, dupe}, true, false);
    CHECK(m.removed == 1);
    CHECK(m.records.size() == 1);
    CHECK(m.records[0].get("time_off") == "194945");

    if (failures == 0) {
        std::cout << "All wsjtx C++ tests passed." << std::endl;
    }
    return failures == 0 ? 0 : 1;
}
