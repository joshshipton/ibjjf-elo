import logging
from progress.bar import Bar
from models import Match, MatchParticipant, Division
from elo import compute_ratings
from current import generate_current_ratings

log = logging.getLogger('ibjjf')

def recompute_all_ratings(db, gi, gender=None, age=None, start_date=None, rerank=True):
    query = db.session.query(Match).join(MatchParticipant).join(Division).filter(
        Division.gi == gi
    )

    if gender is not None:
        query = query.filter(Division.gender == gender)
    if age is not None:
        query = query.filter(Division.age == age)
    if start_date is not None:
        query = query.filter(Match.happened_at >= start_date)

    count = query.count() // 2

    with Bar(f'Recomputing athlete {"gi" if gi else "no-gi"} ratings', max=count) as bar:
        for match in query.order_by(Match.happened_at, Match.id).all():
            bar.next()

            if len(match.participants) != 2:
                log.info(f"Match {match.id} has {len(match.participants)} participants, skipping")
                continue

            count += 1

            red, blue = match.participants
            rated, red_start_rating, red_end_rating, blue_start_rating, blue_end_rating = compute_ratings(db, match.event_id, match.id, match.division, match.happened_at, red.athlete_id, red.winner, red.note, blue.athlete_id, blue.winner, blue.note)

            changed = False

            if red.start_rating != red_start_rating:
                red.start_rating = red_start_rating
                changed = True
            if red.end_rating != red_end_rating:
                red.end_rating = red_end_rating
                changed = True
            if blue.start_rating != blue_start_rating:
                blue.start_rating = blue_start_rating
                changed = True
            if blue.end_rating != blue_end_rating:
                blue.end_rating = blue_end_rating
                changed = True
            if match.rated != rated:
                match.rated = rated
                changed = True

            if changed:
                db.session.flush()

    if rerank:
        log.info("Regenerating ranking board...")
        generate_current_ratings(db)

    return count
