import sys
import os
import zlib


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
        file=sys.argv[3] # file name
        filename=f".git/objects.{file[0:2]}/{file[2:]}"
        with open(filename,"r") as contentfile:
            data=contentfile.read()
            data_decompressed= zlib.decompress(data)
            object_storage_nullbyte=data_decompressed.find("\0")
            content= data_decompressed[object_storage_nullbyte+1 : ]
            sys.stdout.write(content)
    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
