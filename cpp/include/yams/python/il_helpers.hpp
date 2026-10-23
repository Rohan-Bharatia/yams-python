// Copyright (c) 2026 YAMS Python contributors
// SPDX-License-Identifier: LGPL-3.0-or-later
//
// Helpers for invoking C++ APIs that take ``std::initializer_list`` from
// Python-provided sequences.
//
// An ``std::initializer_list`` cannot be constructed from a dynamic buffer via
// the public standard API, so instead we materialise the backing array in the
// caller's frame inside a braced-init-list and invoke the callable immediately.

#pragma once

#include <cstddef>
#include <initializer_list>
#include <stdexcept>
#include <utility>
#include <vector>

namespace yams::python {

namespace detail {

template <typename F, typename T, std::size_t... I>
decltype(auto) call_with_il_impl(F&& f, const std::vector<T>& values, std::index_sequence<I...>) {
  return std::forward<F>(f)(std::initializer_list<T>{values[I]...});
}

template <std::size_t N, typename F, typename T>
decltype(auto) call_with_il_n(F&& f, const std::vector<T>& values) {
  return detail::call_with_il_impl(std::forward<F>(f), values,
                                   std::make_index_sequence<N>{});
}

}  // namespace detail

//: Invoke ``f`` with an ``initializer_list<T>`` built from ``values``.
//:
//: Supports up to 16 elements, which is more than any YAMS initializer_list
//: API is expected to need.
template <typename T, typename F>
decltype(auto) call_with_il(F&& f, const std::vector<T>& values) {
  switch (values.size()) {
    case 0:
      return f(std::initializer_list<T>{});
    case 1:
      return detail::call_with_il_n<1>(std::forward<F>(f), values);
    case 2:
      return detail::call_with_il_n<2>(std::forward<F>(f), values);
    case 3:
      return detail::call_with_il_n<3>(std::forward<F>(f), values);
    case 4:
      return detail::call_with_il_n<4>(std::forward<F>(f), values);
    case 5:
      return detail::call_with_il_n<5>(std::forward<F>(f), values);
    case 6:
      return detail::call_with_il_n<6>(std::forward<F>(f), values);
    case 7:
      return detail::call_with_il_n<7>(std::forward<F>(f), values);
    case 8:
      return detail::call_with_il_n<8>(std::forward<F>(f), values);
    case 9:
      return detail::call_with_il_n<9>(std::forward<F>(f), values);
    case 10:
      return detail::call_with_il_n<10>(std::forward<F>(f), values);
    case 11:
      return detail::call_with_il_n<11>(std::forward<F>(f), values);
    case 12:
      return detail::call_with_il_n<12>(std::forward<F>(f), values);
    case 13:
      return detail::call_with_il_n<13>(std::forward<F>(f), values);
    case 14:
      return detail::call_with_il_n<14>(std::forward<F>(f), values);
    case 15:
      return detail::call_with_il_n<15>(std::forward<F>(f), values);
    case 16:
      return detail::call_with_il_n<16>(std::forward<F>(f), values);
    default:
      throw std::invalid_argument("too many initializer_list elements (max 16)");
  }
}

}  // namespace yams::python
