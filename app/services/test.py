import random,string
    
def _generate_random_id() -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters,k=6))

for _ in range(10):
    random_id = _generate_random_id()
    print(f"- {random_id}")