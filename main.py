from myindexer import MyIndexer
def main():
    """
    Takes in input video path to query and outputs result of query
    """
    while True:
        input_filepath = input("Please enter the relative filepath of the input video:\n")
        query_video = MyIndexer(input_filepath)
        query_video.query_and_display()
        

if __name__ == '__main__':
    main()