#include <NamedType/named_type.hpp>
#include <tuple>

int main() {
    using Meter =
        fluent::NamedType<double, struct MeterParameter, fluent::Addable, fluent::Comparable>;
    Meter m{0};
    m.get();
    return 0;
}
