import socket
import os
import threading
import hashlib

SERVER_HOST = '127.0.0.1'  
SERVER_PORT = 1234         
CLIENT_PORT = 1235         
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), 'public')

def start_file_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', CLIENT_PORT))
    server.listen(5)
    print(f"[*] Servidor de arquivos escutando na porta {CLIENT_PORT}")

    def handle_connection(client_socket):
        try:
            request = client_socket.recv(1024).decode().strip()
            if request.startswith("GET"):
                parts = request.split()
                filename = parts[1]
                # OFFSET - Para os arquivos
                if len(parts) >= 3 and '-' in parts[2]:
                    start, end = parts[2].split('-')
                    offset_start = int(start)
                    offset_end = int(end) if end else None
                else:
                    offset_start = 0
                    offset_end = None

                filepath = os.path.abspath(os.path.join(PUBLIC_DIR, filename))
                if not filepath.startswith(os.path.abspath(PUBLIC_DIR)):
                    client_socket.sendall(b"ERROR: Acesso negado")
                    return

                if not os.path.exists(filepath):
                    client_socket.sendall(b"ERROR: Arquivo nao encontrado")
                    return

                file_size = os.path.getsize(filepath)
                if offset_end is None or offset_end > file_size:
                    offset_end = file_size

                length = offset_end - offset_start

                client_socket.sendall(f"SIZE:{length}".encode())
                if client_socket.recv(1024).decode() != "READY":
                    return

                with open(filepath, 'rb') as f:
                    f.seek(offset_start)
                    sent = 0
                    while sent < length:
                        chunk = f.read(min(4096, length - sent))
                        if not chunk:
                            break
                        client_socket.sendall(chunk)
                        sent += len(chunk)

                print(f"[+] Enviado {filename} ({offset_start}-{offset_end})")

        except Exception as e:
            print(f"[!] Erro no servidor: {str(e)}")
        finally:
            client_socket.close()

    def accept_connections():
        while True:
            try:
                client_sock, addr = server.accept()
                print(f"[+] Conexão recebida de {addr[0]}")
                threading.Thread(
                    target=handle_connection,
                    args=(client_sock,)
                ).start()
            except Exception as e:
                print(f"[!] Erro ao aceitar conexão: {str(e)}")
                break

    threading.Thread(target=accept_connections, daemon=True).start()

def connect_to_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    return sock

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def join_network(server_sock, client_ip):
    server_sock.sendall(f"JOIN {client_ip}:{CLIENT_PORT}".encode())
    response = server_sock.recv(1024).decode()
    print(f"[Servidor] {response}")

def share_files(server_sock):
    if not os.path.exists(PUBLIC_DIR):
        os.makedirs(PUBLIC_DIR)
        print(f"[*] Pasta {PUBLIC_DIR} criada")

    for filename in os.listdir(PUBLIC_DIR):
        filepath = os.path.join(PUBLIC_DIR, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            server_sock.sendall(f"CREATEFILE {filename} {size}".encode())
            print(server_sock.recv(1024).decode())

def search_files(server_sock):
    pattern = input("Digite o termo de busca: ").strip()
    if not pattern:
        print("Termo de busca não pode ser vazio")
        return []

    server_sock.sendall(f"SEARCH {pattern}".encode())
    print("\nResultados da busca:")

    results = []
    data = b""
    while True:
        chunk = server_sock.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"ENDSEARCH" in data:
            break

    data = data.decode().splitlines()
    for line in data:
        if line == "NENHUM_ARQUIVO_ENCONTRADO":
            print("Nenhum arquivo encontrado.")
            return []
        if line == "ENDSEARCH":
            break
        if line.startswith("FILE"):
            parts = line.split()
            file_info = {
                'filename': parts[1],
                'address': parts[2],
                'size': parts[3]
            }
            results.append(file_info)
            print(f"{file_info['filename']} ({file_info['size']} bytes) - {file_info['address']}")

    if not results:
        print("Nenhum arquivo encontrado.")
    return results

def download_file(filename, address):
    try:
        ip, port = address.split(':')
        temp_path = os.path.join(PUBLIC_DIR, f".temp_{filename}")
        final_path = os.path.join(PUBLIC_DIR, filename)

        print(f"[*] Conectando a {ip}:{port}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(10)
            sock.connect((ip, int(port)))
            sock.sendall(f"GET {filename}".encode())
            response = sock.recv(1024).decode()
            if response.startswith("ERROR:"):
                print(f"[!] {response}")
                return False
            elif not response.startswith("SIZE:"):
                print(f"[!] Resposta inesperada: {response}")
                return False

            file_size = int(response.split(':')[1])
            sock.sendall(b"READY")

            received = 0
            md5_hash = hashlib.md5()
            with open(temp_path, 'wb') as f:
                while received < file_size:
                    chunk = sock.recv(min(4096, file_size - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    md5_hash.update(chunk)
                    received += len(chunk)

            os.replace(temp_path, final_path)
            print(f"[✓] Download concluído: {filename} ({file_size} bytes)")
            return True

    except socket.timeout:
        print("[!] Tempo excedido durante o download")
    except Exception as e:
        print(f"[!] Erro durante download: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return False

def download_file_in_parts(filename, address, parts=4):
    try:
        ip, port = address.split(':')
        temp_paths = []

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, int(port)))
            sock.sendall(f"GET {filename}".encode())
            response = sock.recv(1024).decode()
            if not response.startswith("SIZE:"):
                print(f"[!] Resposta inesperada: {response}")
                return False
            file_size = int(response.split(":")[1])
            sock.sendall(b"READY")
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break

        offsets = []
        chunk_size = file_size // parts
        for i in range(parts):
            start = i * chunk_size
            end = (start + chunk_size) if i < parts - 1 else file_size
            offsets.append((start, end))

        for idx, (start, end) in enumerate(offsets):
            print(f"[*] Baixando parte {idx+1}: {start}-{end}")
            temp_path = os.path.join(PUBLIC_DIR, f".part_{idx}_{filename}")
            temp_paths.append(temp_path)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((ip, int(port)))
                sock.sendall(f"GET {filename} {start}-{end}".encode())
                response = sock.recv(1024).decode()
                if not response.startswith("SIZE:"):
                    print(f"[!] Resposta inesperada: {response}")
                    return False
                length = int(response.split(":")[1])
                sock.sendall(b"READY")

                received = 0
                with open(temp_path, 'wb') as f:
                    while received < length:
                        chunk = sock.recv(min(4096, length - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)

        final_path = os.path.join(PUBLIC_DIR, filename)
        with open(final_path, 'wb') as final_file:
            for part in temp_paths:
                with open(part, 'rb') as pf:
                    final_file.write(pf.read())
                os.remove(part)

        print(f"[✓] Download concluído: {filename} ({file_size} bytes)")
        return True

    except Exception as e:
        print(f"[!] Erro: {e}")
        return False

def leave_network(server_sock):
    server_sock.sendall(b"LEAVE")
    print(server_sock.recv(1024).decode())
    server_sock.close()

def print_menu():
    print("\n===== MENU PRINCIPAL =====")
    print("1. Buscar arquivos")
    print("2. Baixar arquivo")
    print("3. Sair da rede")

def main():
    local_ip = get_local_ip()
    print(f"\n[*] Seu IP: {local_ip}")
    print(f"[*] Pasta compartilhada: {os.path.abspath(PUBLIC_DIR)}")
    start_file_server()

    try:
        server_sock = connect_to_server()
        join_network(server_sock, local_ip)
        share_files(server_sock)

        while True:
            print_menu()
            choice = input("Escolha uma opção: ").strip()

            if choice == '1':
                search_files(server_sock)
            elif choice == '2':
                filename = input("Nome do arquivo: ").strip()
                address = input("Endereço (IP:Porta): ").strip()
                if not filename or not address:
                    print("Entrada inválida")
                    continue
                modo = input("Modo de download (1 = simples, 2 = em partes): ").strip()
                if modo == '1':
                    download_file(filename, address)
                else:
                    download_file_in_parts(filename, address)
            elif choice == '3':
                leave_network(server_sock)
                break
            else:
                print("Opção inválida")

    except KeyboardInterrupt:
        print("\n[*] Desconectando...")
        leave_network(server_sock)
    except Exception as e:
        print(f"[!] Erro fatal: {str(e)}")

if __name__ == '__main__':
    main()
