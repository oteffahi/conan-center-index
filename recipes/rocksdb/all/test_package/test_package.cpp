#include "rocksdb/db.h"
#include <cstdlib>
#include <iostream>

int main() {
    rocksdb::DB *db;
    rocksdb::Options options;
    options.create_if_missing = true;
    rocksdb::Status status = rocksdb::DB::Open(options, "testdb", &db);

    if (!status.ok()) {
        std::cerr << "DB error: " << status.ToString() << std::endl;
    }
    delete db;
    return EXIT_SUCCESS;
}
