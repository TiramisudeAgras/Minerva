# add_search_index.py - Run this once to add the search index to your existing database

import sqlite3

DATABASE_NAME = 'minerva_icfes_data.db'

def add_search_index():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    print("Adding search optimization index to existing database...")
    
    try:
        # This index will make name searches much faster
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_school_name_search 
        ON school_statistics(periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento)
        """)
        
        # Optional: This one helps with the ORDER BY in search queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_school_search_with_avg 
        ON school_statistics(periodo, cole_depto_ubicacion_norm, cole_nombre_establecimiento, avg_punt_global DESC)
        """)
        
        conn.commit()
        print("✓ Search indexes added successfully!")
        
        # Verify the indexes were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_school_%search%'")
        indexes = cursor.fetchall()
        print(f"✓ Created {len(indexes)} search indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")
            
    except Exception as e:
        print(f"Error adding indexes: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    add_search_index()