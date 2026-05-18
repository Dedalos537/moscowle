import socket
import threading
import sys
import ssl

LISTEN_PORT = 14000
TIDB_HOST = 'gateway01.us-east-1.prod.aws.tidbcloud.com'
TIDB_PORT = 4000
TIDB_SSL_CA = '/etc/ssl/cert.pem'

def forward(src, dst, name):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

def handle_client(client_sock):
    try:
        ctx = ssl.create_default_context(cafile=TIDB_SSL_CA)
        tidb_sock = socket.socket()
        tidb_sock.settimeout(30)
        tidb_sock.connect((TIDB_HOST, TIDB_PORT))
        tidb_ssl = ctx.wrap_socket(tidb_sock, server_hostname=TIDB_HOST)
        
        t1 = threading.Thread(target=forward, args=(client_sock, tidb_ssl, 'C->T'), daemon=True)
        t2 = threading.Thread(target=forward, args=(tidb_ssl, client_sock, 'T->C'), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        try:
            client_sock.sendall(f'PROXY ERROR: {e}\n'.encode())
        except:
            pass
    finally:
        try: client_sock.close()
        except: pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', LISTEN_PORT))
    server.listen(10)
    print(f'TiDB proxy listening on port {LISTEN_PORT}', flush=True)
    while True:
        client, addr = server.accept()
        print(f'Connection from {addr}', flush=True)
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()

if __name__ == '__main__':
    main()
