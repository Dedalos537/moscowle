import asyncio
import ssl
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('tidb-proxy')

TIDB_HOST = os.environ.get('TIDB_HOST', 'gateway01.us-east-1.prod.aws.tidbcloud.com')
TIDB_PORT = int(os.environ.get('TIDB_PORT', '4000'))
LISTEN_PORT = int(os.environ.get('PORT', '4000'))

async def forward(reader, writer, name):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        log.warning(f'Forward error ({name}): {e}')
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except:
            pass

async def handle_client(client_reader, client_writer):
    peername = client_writer.get_extra_info('peername')
    log.info(f'New connection from {peername}')
    
    try:
        ctx = ssl.create_default_context()
        tidb_reader, tidb_writer = await asyncio.open_connection(
            TIDB_HOST, TIDB_PORT,
            ssl=ctx,
            server_hostname=TIDB_HOST
        )
    except Exception as e:
        log.error(f'Failed to connect to TiDB: {e}')
        client_writer.close()
        return

    t1 = asyncio.create_task(forward(client_reader, tidb_writer, 'C->T'))
    t2 = asyncio.create_task(forward(tidb_reader, client_writer, 'T->C'))
    
    try:
        await asyncio.gather(t1, t2)
    except:
        pass
    
    try:
        client_writer.close()
        await client_writer.wait_closed()
    except:
        pass
    try:
        tidb_writer.close()
        await tidb_writer.wait_closed()
    except:
        pass
    
    log.info(f'Connection closed from {peername}')

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', LISTEN_PORT)
    log.info(f'TiDB Proxy listening on port {LISTEN_PORT}')
    log.info(f'Forwarding to {TIDB_HOST}:{TIDB_PORT} with SSL')
    
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
