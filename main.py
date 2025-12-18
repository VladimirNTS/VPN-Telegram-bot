import uvicorn
from dotenv import load_dotenv
load_dotenv()


def main():
    uvicorn.run(app="app.app:app", host='0.0.0.0', port=443, reload=True)


if __name__ == "__main__":
    main()
