import unittest
from belissibot_framework import parse_py_args


class ParsePyArgsTest(unittest.TestCase):
    def test_whitespace(self):
        self.assertEqual(parse_py_args(''), [])
        self.assertEqual(parse_py_args(' '), [])

    def test(self):
        self.assertEqual(parse_py_args('"test"'), ["test"])
        self.assertEqual(parse_py_args('"test" '), ["test"])
        self.assertEqual(parse_py_args('"test" "test"'), ["test", "test"])
        self.assertEqual(parse_py_args('"test" 1'), ["test", 1])
        self.assertEqual(parse_py_args('"test"1'), [])
        self.assertEqual(parse_py_args('512'), [512])
        self.assertEqual(parse_py_args('1 2 3 4 5'), [1, 2, 3, 4, 5])


if __name__ == '__main__':
    unittest.main()
