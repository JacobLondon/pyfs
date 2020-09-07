from filetypes import File

class TestFile(File):
    def __init__(self, *args):
        super().__init__(*args)
        print("Imported!")
