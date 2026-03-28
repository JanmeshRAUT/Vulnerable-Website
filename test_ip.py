import hashlib

def get_lab4_2_target_ip(identity_key, variant='a'):
    seed = f"{identity_key}-lab4-2-{variant}-secret"
    hash_val = int(hashlib.md5(seed.encode()).hexdigest(),  16)
    return (hash_val % 254) + 1

# Case 1: No GUID (None)
print(f"Target IP for None (Variation A): 192.168.0.{get_lab4_2_target_ip(None, 'a')}")
print(f"Target IP for None (Variation B): 192.168.0.{get_lab4_2_target_ip(None, 'b')}")
print(f"Target IP for None (Variation C): 192.168.0.{get_lab4_2_target_ip(None, 'c')}")
