#include <print>
#include <absl/strings/str_cat.h>

auto main() -> int
{
    auto msg = absl::StrCat("NonQtAbslPresetCheck: absl::StrCat works with C++", std::to_string(__cplusplus));
    std::print("{}\n", msg);
    return 0;
}
