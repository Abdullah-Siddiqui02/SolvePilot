from flask import Blueprint, jsonify, request, render_template
import requests
from extensions import get_db

problems_bp = Blueprint("problems", __name__)

@problems_bp.route("/ide", methods=["GET"])
def ide():
    """Render the IDE interface."""
    return render_template("ide.html")

@problems_bp.route("/api/problems/sync", methods=["POST"])
def sync_problems():
    """
    Fetches problems from Codeforces API and stores exactly:
    40 Easy, 20 Medium, 40 Hard problems in the database.
    """
    try:
        response = requests.get("https://codeforces.com/api/problemset.problems")
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch from Codeforces"}), 500

        data = response.json()
        if data.get("status") != "OK":
            return jsonify({"error": "Codeforces API error"}), 500

        all_problems = data["result"]["problems"]
        
        db, cursor = get_db()
        
        easy_count = 0
        medium_count = 0
        hard_count = 0
        
        inserted_count = 0
        
        for prob in all_problems:
            if easy_count >= 40 and medium_count >= 20 and hard_count >= 40:
                break # We have fetched enough problems
                
            platform = "Codeforces"
            contest_id = prob.get("contestId")
            index = prob.get("index")
            if not contest_id or not index:
                continue
                
            problem_id = f"{contest_id}{index}"
            title = prob.get("name")
            tags = ",".join(prob.get("tags", []))
            url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
            
            # Difficulty mapping approximation for Codeforces
            rating = prob.get("rating", 0)
            if rating == 0:
                continue # Skip unrated problems
                
            if rating <= 1200:
                if easy_count >= 40: continue
                difficulty = "Easy"
                easy_count += 1
            elif rating <= 1600:
                if medium_count >= 20: continue
                difficulty = "Medium"
                medium_count += 1
            else:
                if hard_count >= 40: continue
                difficulty = "Hard"
                hard_count += 1

            try:
                cursor.execute(
                    """
                    INSERT INTO global_problems (platform, platform_problem_id, title, difficulty, tags, url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        title = VALUES(title), difficulty = VALUES(difficulty), tags = VALUES(tags), url = VALUES(url)
                    """,
                    (platform, problem_id, title, difficulty, tags, url)
                )
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting problem {problem_id}: {e}")
                
        db.commit()
        cursor.close()
        
        return jsonify({
            "message": "Successfully synced problems.",
            "stats": {
                "total_inserted_or_updated": inserted_count,
                "easy": easy_count,
                "medium": medium_count,
                "hard": hard_count
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@problems_bp.route("/api/problems", methods=["GET"])
def get_problems():
    """Retrieve cached problems from the local database."""
    difficulty = request.args.get("difficulty")
    platform = request.args.get("platform")
    
    db, cursor = get_db()
    
    query = "SELECT * FROM global_problems WHERE 1=1"
    params = []
    
    if difficulty:
        query += " AND difficulty = %s"
        params.append(difficulty)
    if platform:
        query += " AND platform = %s"
        params.append(platform)
        
    query += " ORDER BY id DESC LIMIT 100"
    
    cursor.execute(query, tuple(params))
    problems = cursor.fetchall()
    
    column_names = [col[0] for col in cursor.description]
    problem_dicts = [dict(zip(column_names, row)) for row in problems]
    
    cursor.close()
    
    return jsonify({"problems": problem_dicts})
