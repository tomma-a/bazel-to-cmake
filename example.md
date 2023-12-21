Take tcmalloc as an example:
python bazel_to_cmake.py -t a.py -s '//tcmalloc/internal:'  -o jj.txt tcmalloc/BUILD  tcmalloc/internal/BUILD
