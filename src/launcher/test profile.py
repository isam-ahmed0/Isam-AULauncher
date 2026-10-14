from itch_oauth import fetch_itch_profile, fetch_itch_username, read_itch_token

# its just a test and checking if it works so.
prefix = "/home/isam/.wine/"

def test_profile():
    token = read_itch_token(prefix)
    username = fetch_itch_username(prefix)
    profile = fetch_itch_profile(prefix, username=username)
    
    return profile

profile = test_profile()

for key, value in profile.items():
    print(f"{key}: {value}")