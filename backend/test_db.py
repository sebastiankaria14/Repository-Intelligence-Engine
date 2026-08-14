import asyncio
import asyncpg

async def test():
    for user in ['postgres', 'rie', 'postgresql']:
        for pwd in ['', 'postgres', 'admin', 'rie_secret_change_me']:
            try:
                conn = await asyncpg.connect(f'postgresql://{user}:{pwd}@localhost:5432/postgres')
                print(f'SUCCESS: {user}:{pwd or "(empty)"}')
                await conn.close()
                return
            except Exception as e:
                pass
    print('no credentials worked')

asyncio.run(test())
