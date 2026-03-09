import time
from google import genai

def main():
    print("=" * 60)
    print("AI PyBot Initialized!")
    print("=" * 60)
    
    print("\nBefore we begin, you need a Google Gemini API Key.")
    print("You can get a free one here: https://aistudio.google.com/app/apikey")
    
    api_key = input("\nPlease paste your API key here (or press Enter to quit): ").strip()
    
    if not api_key:
        print("No API key provided. Exiting...")
        return
        
    try:
        # Initialize the client
        client = genai.Client(api_key=api_key)
        
        # Start a chat session using gemini-2.5-flash
        chat = client.chats.create(model="gemini-2.5-flash")
        
        print("\n" + "=" * 60)
        print("Connection successful! The AI is ready to chat.")
        print("Type 'quit' or 'exit' at any time to stop the conversation.")
        print("=" * 60)
        
        while True:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ["bye", "goodbye", "exit", "quit"]:
                print("AI PyBot: Goodbye! Have a great day!")
                break
                
            if not user_input:
                continue
            
            # Send message to Gemini and get response
            print("AI PyBot is typing...", end="\r")
            
            try:
                response = chat.send_message(user_input)
                # Clear the "typing..." message and print actual response
                print(" " * 20, end="\r") 
                print(f"AI PyBot: {response.text}")
                
            except Exception as e:
                print(" " * 20, end="\r")
                print(f"AI PyBot Error: Oops, I couldn't get a response. ({e})")
                
    except KeyboardInterrupt:
        print("\n\nAI PyBot: Program interrupted. Goodbye!")
    except Exception as e:
        print(f"\nAI PyBot Initialization Error: {e}")

if __name__ == "__main__":
    main()
