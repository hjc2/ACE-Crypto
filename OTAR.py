# importing libraries
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.hmac import hashes, HMAC
from datetime import datetime, timedelta


class Client:

    def __init__(self):
        
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048, # 2048 is a happy-medium between security and performance
        )
        self.public_key = self.private_key.public_key()
        self.symmetric_key = None

    def get_public_key(self):
        return self.public_key
    
    def set_symmetric_key(self, key):
        self.symmetric_key = key

    # Sign the message using the private key
    def sign_message(self, message):
        signature = self.private_key.sign(
            message,
            padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        return signature
    
    # Decrypt the ciphertext using the private key
    def decrypt_asymmetric_message(self, ciphertext):

        message = self.private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return message
    
    # Add the timestamp and encrypt the message using the symmetric key 
    def encrypt_symmetric_message(self, message):
        message = message +  bytes(" ~ " + str(datetime.now()), 'UTF-8')
        return Fernet(self.symmetric_key).encrypt(message)
    
    # Decrypt the encrypted message using the symmetric key, then verify the timestamp
    def decrypt_symmetric_message(self, ciphertext):
        output = Fernet(self.symmetric_key).decrypt(ciphertext)
        if self.vertifyTimestamp(output):
            return output
        else:
            return b"Message failed, invalid timestamp!"
    
    # Create the HMAC using athe encrypted message and symmetric key
    def create_hmac(self, data):
        h = HMAC(self.symmetric_key, hashes.SHA256())
        h.update(data)
        return h.finalize()
    
    # Verify the HMAC using the encrypted message and symmetric key
    def verify_hmac(self, data, tag):
        h = HMAC(self.symmetric_key, hashes.SHA256())
        h.update(data)
        h.verify(tag)

# The following are functions that can be utilized by anyone because they do not contain private data:

# Verify the timestamp of a message to prevent replay attacks
    def vertifyTimestamp(self, data):
        date_format = "%Y-%m-%d %H:%M:%S.%f"

        data = data.decode("utf-8").split(" ~ ")[1]
        date_data = datetime.strptime(data, date_format)

        return(abs(datetime.now() - date_data) < timedelta(seconds=30))

# Encrypt a message using the recipient's public key
def encrypt_message(public_key, message):
    ciphertext = public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext

# Verify a message using the sender's public key
def verify_message(public_key, signature, message):
    
    return public_key.verify(
        signature,
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )


def main():

    client = Client()
    client_public_key = client.get_public_key()

    radio = Client()
    radio_public_key = radio.get_public_key()

    print("Creating symmetric key:")

    symmetric_key = Fernet.generate_key()
    radio.set_symmetric_key(symmetric_key)

    print("Starting asymmetric key exchange and signature:")

    ciphertext = encrypt_message(client_public_key, symmetric_key)

    signature = radio.sign_message(ciphertext)

    verify_message(radio_public_key, signature, ciphertext)

    output = client.decrypt_asymmetric_message(ciphertext)
    client.set_symmetric_key(output)

    print("Starting symmetric encryption: ")

    # radio sends secret message to client
    secret_message = b"This is the secret message."

    encrypted = radio.encrypt_symmetric_message(secret_message)

    HMAC1 = radio.create_hmac(encrypted)

    client.verify_hmac(encrypted, HMAC1)

    decrypted_message = client.decrypt_symmetric_message(encrypted)

    print(decrypted_message)

    # client sends secret message to radio
    secret_message_2 = b"Received secret message."

    encrypted_2 = client.encrypt_symmetric_message(secret_message_2)

    HMAC2 = radio.create_hmac(encrypted_2)

    radio.verify_hmac(encrypted_2, HMAC2)

    decrypted_message_2 = radio.decrypt_symmetric_message(encrypted_2)

    print(decrypted_message_2)


if __name__ == '__main__':
    main()