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

    elif command == "ls-tree":
        tree_sha = sys.argv[3]
        fname = f".git/objects/{tree_sha[0:2]}/{tree_sha[2:]}"
        with open(fname, "rb") as contentfile:
            #tree <size>\0
            #<mode> <name>\0<20_byte_sha>
            #<mode> <name>\0<20_byte_sha>
            try:
                data = contentfile.read()
                data_decompressed = zlib.decompress(data)
                tree_header,tree_data= data_decompressed.split(b"\x00",maxsplit=1)
            except FileNotFoundError:
                print("fatal: object not found", file=sys.stderr)
                sys.exit(1)
            
            while tree_data:
                mode_name,tree_data=tree_data.split(b"\x00",maxsplit=1)
                mode,name=mode_name.split()

                #For w/o --nameonly
                # name_decoded=name.decode("utf-8")
                # mode_decoded=mode.decode("utf-8")
                # if mode_decoded.startswith("4"):
                #     obj_type = "tree"
                # else:
                #     obj_type = "blob"

                # print(mode_decoded,' ',obj_type,' ',tree_data[:20],name_decoded,end="\n")

                print(name.decode("utf-8"))
                tree_data=tree_data[20:]

    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
