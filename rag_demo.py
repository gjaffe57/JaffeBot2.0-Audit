import json
from gsc_rag import GSCRAG
import argparse

def load_gsc_data(file_path: str) -> list:
    """Load GSC data from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description='GSC RAG Demo')
    parser.add_argument('--data', required=True, help='Path to GSC data JSON file')
    parser.add_argument('--query', help='Query to run against the RAG system')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    args = parser.parse_args()

    # Initialize RAG system
    rag = GSCRAG()

    # Load GSC data
    print(f"Loading GSC data from {args.data}...")
    gsc_data = load_gsc_data(args.data)

    # Create vector store
    print("Creating vector store...")
    rag.create_vector_store(gsc_data)

    # Setup QA chain
    print("Setting up QA chain...")
    rag.setup_qa_chain()

    if args.interactive:
        print("\nEnter your queries (type 'exit' to quit):")
        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'exit':
                break
            try:
                response = rag.query(query)
                print(f"\nResponse: {response}")
            except Exception as e:
                print(f"Error: {str(e)}")
    elif args.query:
        try:
            response = rag.query(args.query)
            print(f"\nQuery: {args.query}")
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("Please provide either --query or --interactive flag")

if __name__ == "__main__":
    main() 