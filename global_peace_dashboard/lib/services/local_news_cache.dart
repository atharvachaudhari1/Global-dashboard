import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';
import '../models/article.dart';

class LocalNewsCache {
  static const _dbName = 'global_peace_cache.db';
  static const _table = 'articles';
  static Database? _db;

  static Future<Database> _database() async {
    if (_db != null) return _db!;
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, _dbName);
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE $_table (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            source TEXT,
            country TEXT,
            pubDate TEXT,
            link TEXT,
            apiSource TEXT,
            score REAL,
            category TEXT,
            color TEXT,
            cls TEXT,
            cachedAt TEXT
          )
        ''');
      },
    );
    return _db!;
  }

  static Future<void> saveArticles(List<Article> articles) async {
    final db = await _database();
    final batch = db.batch();
    for (final article in articles) {
      batch.insert(
        _table,
        article.toMap(),
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
    await _enforceCapacity(db);
  }

  static Future<List<Article>> readArticles({int limit = 50000}) async {
    final db = await _database();
    final rows = await db.query(
      _table,
      orderBy: 'pubDate DESC, cachedAt DESC',
      limit: limit,
    );
    return rows.map(Article.fromMap).toList();
  }

  static Future<int> countArticles() async {
    final db = await _database();
    final res = await db.rawQuery('SELECT COUNT(*) AS c FROM $_table');
    return (res.first['c'] as int?) ?? 0;
  }

  static Future<void> _enforceCapacity(
    Database db, {
    int maxRows = 50000,
    int pruneBatch = 1000,
  }) async {
    final res = await db.rawQuery('SELECT COUNT(*) AS c FROM $_table');
    final total = (res.first['c'] as int?) ?? 0;
    if (total <= maxRows) return;

    await db.rawDelete('''
      DELETE FROM $_table
      WHERE id IN (
        SELECT id FROM $_table
        ORDER BY pubDate ASC, cachedAt ASC
        LIMIT ?
      )
    ''', [pruneBatch]);
  }
}
