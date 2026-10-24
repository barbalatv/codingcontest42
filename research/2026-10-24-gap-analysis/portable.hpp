#pragma once
#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>
#ifdef _MSC_VER
#define __builtin_popcountll(x) std::popcount(static_cast<unsigned long long>(x))
#define __builtin_ctzll(x) std::countr_zero(static_cast<unsigned long long>(x))
#endif
