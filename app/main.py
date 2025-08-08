import sys
import os
import zlib
import hashlib


def cat_file_blob(fname):
    with open(fname, "rb") as contentfile:
        data = contentfile.read()
        data_decompressed = zlib.decompress(data).decode("utf-8")
        obj_storage_nullbyte = data_decompressed.find("\x00")
        content = data_decompressed[obj_storage_nullbyte+1:].strip()
        print(content, end="")


def hash_object_blob(filedata):
    header = f"blob {len(filedata)}\x00".encode("utf-8")
    file = header + filedata
    hashed_file = hashlib.sha1(file).hexdigest()
    print(hashed_file)
    hash_dir = os.path.join(".git/objects", hashed_file[0:2])
    os.mkdir(hash_dir)
    # If we also need to write
    if sys.argv[2] == '-w':
        with open(os.path.join(hash_dir, hashed_file[2:]), "wb") as fp:
            fp.write(zlib.compress(file))


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    command = sys.argv[1]
    if command == "init":
        os.mkdir(".git")
        os.mkdir(".git/objects")
        os.mkdir(".git/refs")
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")

    elif command == "cat-file":
        file = sys.argv[3]  # file name
        # based on the task info
        filename = f".git/objects/{file[0:2]}/{file[2:]}"
        cat_file_blob(filename)

        # with open(filename, "rb") as contentfile:
        #     data = contentfile.read()
        #     data_decompressed = zlib.decompress(data).decode("utf-8")
        #     obj_storage_nullbyte = data_decompressed.find("\x00")
        #     content = data_decompressed[obj_storage_nullbyte+1:].strip()
        #     print(content, end="")

    elif command == "hash-object":
        with open(sys.argv[3], "rb") as f:
            fdata = f.read()
        hash_object_blob(fdata)
        # header = f"blob {len(filedata)}\x00".encode("utf-8")
        # file = header + filedata
        # hashed_file = hashlib.sha1(file).hexdigest()
        # print(hashed_file)
        # hash_dir = os.path.join(".git/objects", hashed_file[0:2])
        # os.mkdir(hash_dir)
        # # If we also need to write
        # if sys.argv[2] == '-w':
        #     with open(os.path.join(hash_dir, hashed_file[2:]), "wb") as fp:
        #         fp.write(zlib.compress(file))
            # hash=hashlib.sha1(res).hexdigest()
            # print(hash)

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
