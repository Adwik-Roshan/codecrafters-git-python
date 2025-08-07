import sys
import os
import zlib


def cat_file_blob(fname):
    with open(fname, "rb") as contentfile:
        data = contentfile.read()
        data_decompressed = zlib.decompress(data).decode("utf-8")
        obj_storage_nullbyte = data_decompressed.find("\x00")
        content = data_decompressed[obj_storage_nullbyte+1:].strip()
        print(content, end="")


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

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
