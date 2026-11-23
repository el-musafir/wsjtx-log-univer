#ifndef WSJTX_UNIFY_HPP
#define WSJTX_UNIFY_HPP

#include <vector>

#include "adi.hpp"

namespace adi {
namespace unify {

struct UnifyResult {
    QsoRecordVec records;
    int removed = 0;
};

// Merge records into one unified list. With dedupe, repeated QSOs (same
// call, band, date/time and mode) collapse to a single record; with sort,
// the result is ordered by qso_date then time_on.
UnifyResult unifyRecords(const QsoRecordVec& records, bool dedupe = true,
                         bool sort = true);

}  // namespace unify
}  // namespace adi

#endif  // WSJTX_UNIFY_HPP
