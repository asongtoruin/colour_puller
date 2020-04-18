import sqlite3


class AlbumDatabase:
    def __init__(self, db_path='spotify albums.sqlite'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Get responses as dictionary
        self.conn.row_factory = sqlite3.Row

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                name text NOT NULL,
                artists text NOT NULL,
                release_date text NOT NULL,
                link text,
                art_link text NOT NULL,
                status text DEFAULT "queued"
            )
            '''
        )

        self.conn.commit()

    def contains_album(self, info_dict):
        self.cursor.execute('''
            SELECT * FROM albums WHERE
                name = ?
                AND artists = ?
                AND release_date = ?
            LIMIT 1
            ''',
            (info_dict['name'], info_dict['artists'], info_dict['release_date'])
        )

        resp = self.cursor.fetchone()

        return len(resp) > 0

    def add_albums(self, albums):
        self.cursor.executemany('''
            INSERT INTO albums (
                name, artists, release_date, link, art_link
            )
            VALUES (?, ?, ?, ?, ?)
            ''',
            [
                (
                    album['name'], album['artists'], album['release_date'],
                    album['link'], album['art_link']
                )
                for album in albums
            ]
        )

        self.conn.commit()

    def update_album(self, info_dict, status='processing'):
        if not status in ('queued', 'processing', 'completed'):
            raise ValueError(
                'status should be one of "queued", "processing" or "completed", '
                f'received {status}'
            )
        
        self.cursor.execute('''
            UPDATE albums
            SET status=?
            WHERE
                name = ?
                AND artists = ?
                AND release_date = ?
                AND link = ?
                AND art_link = ?
            ''',
            (
                status, info_dict['name'], info_dict['artists'], 
                info_dict['release_date'], info_dict['link'], 
                info_dict['art_link']
            )
        )

        self.conn.commit()