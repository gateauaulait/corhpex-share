#ifndef __PARAM_TYPES_H
#define __PARAM_TYPES_H
#include <functional>
#include <stddef.h>

// =====================================================

enum class FPType { Float = 0, Double, _count, begin = 0, end = _count };

// =====================================================

using ConfigId = std::tuple<FPType, FPType>;
using FnBench = std::function<int(int, long unsigned int)>;

#endif // __PARAM_TYPES_H
