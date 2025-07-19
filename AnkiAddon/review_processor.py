# review_processor.py - Review Data Processing (Enhanced)
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from aqt import mw

class ReviewProcessor:
    """Handles review data extraction from Anki's existing data"""
    
    def __init__(self):
        self.session_gap_minutes = 30  # Gap to consider separate sessions
    
    def get_recent_sessions(self, days_back: int = 7) -> List[Dict[str, Any]]:
        """Extract session data from Anki's review log"""
        if not mw.col:
            return []
        
        try:
            # Get cutoff timestamp
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            # Query Anki's review log
            reviews = mw.col.db.all("""
                SELECT id, cid, usn, ease, ivl, lastIvl, factor, time, type
                FROM revlog 
                WHERE id > ?
                ORDER BY id ASC
            """, cutoff_timestamp)
            
            if not reviews:
                return []
            
            # Convert to review objects and group into sessions
            review_objects = self._parse_reviews(reviews)
            sessions = self._group_reviews_into_sessions(review_objects)
            
            # Calculate session metrics
            session_metrics = [self._calculate_session_metrics(session) for session in sessions]
            
            # Group sessions by date and deck, then merge
            merged_sessions = self._merge_sessions_by_date_and_deck(session_metrics)
            
            return merged_sessions
            
        except Exception as e:
            print(f"Error getting recent sessions: {e}")
            return []
    
    def get_latest_session_only(self) -> Optional[Dict[str, Any]]:
        """Get only the latest session (today's merged session)"""
        try:
            # Get today's sessions
            today_sessions = self.get_recent_sessions(1)  # Last 1 day
            
            if not today_sessions:
                return None
            
            # Return the most recent session (should be today's merged session)
            return today_sessions[-1] if today_sessions else None
            
        except Exception as e:
            print(f"Error getting latest session: {e}")
            return None
    
    def get_current_deck_state(self, deck_name: str = None) -> Dict[str, Any]:
        """Get current state for specific deck: due cards, overdue, etc."""
        if not mw.col:
            print("No collection available")
            return {}
        
        try:
            # Get deck ID from name
            deck_id = None
            if deck_name:
                try:
                    deck_id = mw.col.decks.id(deck_name)
                    print(f"Using deck: {deck_name} (ID: {deck_id})")
                except Exception as e:
                    print(f"Error getting deck ID for '{deck_name}': {e}")
                    # Continue with all decks if specific deck not found
            
            # Get current counts from scheduler - with error handling
            try:
                if deck_id:
                    # Get counts for specific deck
                    cards_due_today, new_cards_available = self._get_deck_specific_counts(deck_id)
                else:
                    # Get counts for all decks
                    counts = mw.col.sched.counts()
                    cards_due_today = counts.learn + counts.review
                    new_cards_available = counts.new
            except Exception as e:
                print(f"Error getting scheduler counts: {e}")
                # Fallback: query database directly
                cards_due_today = self._get_due_cards_fallback(deck_id)
                new_cards_available = self._get_new_cards_fallback(deck_id)
            
            # Count overdue cards for specific deck
            try:
                overdue_count = self._get_overdue_cards_count(deck_id)
            except Exception as e:
                print(f"Error counting overdue cards: {e}")
                overdue_count = 0
            
            # Get total cards for specific deck
            try:
                total_cards = self._get_total_cards_count(deck_id)
            except Exception as e:
                print(f"Error getting total card count: {e}")
                total_cards = 0
            
            # Get last session date
            last_session_date = self._get_last_session_date()
            
            result = {
                "cards_due_today": cards_due_today,
                "new_cards_available": new_cards_available,
                "cards_overdue": overdue_count,
                "total_cards": total_cards,
                "last_session_date": last_session_date,
                "deck_name": deck_name or "All Decks"
            }
            
            print(f"Current deck state for '{deck_name or 'All Decks'}': {result}")
            return result
            
        except Exception as e:
            print(f"Error getting current deck state: {e}")
            return {
                "cards_due_today": 0,
                "new_cards_available": 0,
                "cards_overdue": 0,
                "total_cards": 0,
                "last_session_date": None,
                "deck_name": deck_name or "All Decks",
                "error": str(e)
            }
    
    def get_current_deck_state(self, deck_name: str = None) -> Dict[str, Any]:
        """Get current state for specific deck: due cards, overdue, etc."""
        if not mw.col:
            print("No collection available")
            return {}
        
        try:
            # Get deck ID from name
            deck_id = None
            if deck_name:
                try:
                    deck_id = mw.col.decks.id(deck_name)
                    print(f"Using deck: {deck_name} (ID: {deck_id})")
                except Exception as e:
                    print(f"Error getting deck ID for '{deck_name}': {e}")
                    # Try to find deck by name pattern
                    deck_id = self._find_deck_by_name(deck_name)
            
            # Get current counts
            try:
                if deck_id:
                    # Get counts for specific deck
                    cards_due_today, new_cards_available, overdue_count, total_cards = self._get_deck_counts(deck_id)
                else:
                    # Get counts for all decks
                    counts = mw.col.sched.counts()
                    cards_due_today = counts.learn + counts.review
                    new_cards_available = counts.new
                    
                    today = int(datetime.now().timestamp() / 86400)
                    overdue_count = mw.col.db.scalar("""
                        SELECT COUNT(*) FROM cards WHERE queue >= 0 AND due < ?
                    """, today) or 0
                    
                    total_cards = mw.col.card_count()
                    
            except Exception as e:
                print(f"Error getting deck counts: {e}")
                cards_due_today = new_cards_available = overdue_count = total_cards = 0
            
            # Get last session date
            last_session_date = self._get_last_session_date()
            
            result = {
                "cards_due_today": cards_due_today,
                "new_cards_available": new_cards_available,
                "cards_overdue": overdue_count,
                "total_cards": total_cards,
                "last_session_date": last_session_date,
                "deck_name": deck_name or "All Decks",
                "deck_id": deck_id
            }
            
            print(f"Current deck state for '{deck_name or 'All Decks'}': {result}")
            return result
            
        except Exception as e:
            print(f"Error getting current deck state: {e}")
            return {
                "cards_due_today": 0,
                "new_cards_available": 0,
                "cards_overdue": 0,
                "total_cards": 0,
                "last_session_date": None,
                "deck_name": deck_name or "All Decks",
                "error": str(e)
            }
    
    def _find_deck_by_name(self, deck_name: str) -> Optional[int]:
        """Find deck ID by name, including partial matches"""
        try:
            # Get all decks
            all_decks = mw.col.decks.all()
            
            print(f"Available decks:")
            for deck in all_decks:
                print(f"  - {deck['name']} (ID: {deck['id']})")
            
            # Try exact match first
            for deck in all_decks:
                if deck['name'] == deck_name:
                    print(f"Found exact match: {deck['name']} (ID: {deck['id']})")
                    return deck['id']
            
            # Try partial match
            for deck in all_decks:
                if deck_name.lower() in deck['name'].lower():
                    print(f"Found partial match: {deck['name']} (ID: {deck['id']})")
                    return deck['id']
            
            print(f"No deck found matching '{deck_name}'")
            return None
            
        except Exception as e:
            print(f"Error finding deck by name: {e}")
            return None
    
    def _get_deck_counts(self, deck_id: int) -> tuple:
        """Get all counts for specific deck"""
        try:
            today = int(datetime.now().timestamp() / 86400)
            
            print(f"Getting counts for deck ID: {deck_id}")
            
            # Debug: Check what cards exist for this deck
            all_cards = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards WHERE did = ?
            """, deck_id) or 0
            print(f"Total cards in deck: {all_cards}")
            
            # Get due cards (learning + review queues that are due today or earlier)
            due_count = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards 
                WHERE did = ? AND queue IN (1, 2, 3) AND due <= ?
            """, deck_id, today) or 0
            print(f"Due cards: {due_count}")
            
            # Get new cards (queue 0)
            new_count = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards 
                WHERE did = ? AND queue = 0
            """, deck_id) or 0
            print(f"New cards: {new_count}")
            
            # Get overdue cards (due before today)
            overdue_count = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards 
                WHERE did = ? AND queue IN (1, 2, 3) AND due < ?
            """, deck_id, today) or 0
            print(f"Overdue cards: {overdue_count}")
            
            # Total cards in deck
            total_count = all_cards
            
            # Debug: Show queue distribution
            queue_counts = mw.col.db.all("""
                SELECT queue, COUNT(*) FROM cards WHERE did = ? GROUP BY queue
            """, deck_id)
            print(f"Queue distribution: {queue_counts}")
            
            return due_count, new_count, overdue_count, total_count
            
        except Exception as e:
            print(f"Error getting deck counts: {e}")
            return 0, 0, 0, 0
    
    def _get_deck_specific_counts(self, deck_id: int) -> tuple:
        """Get due and new card counts for specific deck"""
        try:
            today = int(datetime.now().timestamp() / 86400)
            
            # Get due cards (learning + review) for this deck
            due_count = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards 
                WHERE did = ? AND queue IN (1, 2, 3) AND due <= ?
            """, deck_id, today) or 0
            
            # Get new cards for this deck
            new_count = mw.col.db.scalar("""
                SELECT COUNT(*) FROM cards 
                WHERE did = ? AND queue = 0
            """, deck_id) or 0
            
            return due_count, new_count
            
        except Exception as e:
            print(f"Error getting deck specific counts: {e}")
            return 0, 0
    
    def _get_due_cards_fallback(self, deck_id: int = None) -> int:
        """Fallback method to get due cards count"""
        try:
            today = int(datetime.now().timestamp() / 86400)
            
            if deck_id:
                due_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE did = ? AND queue >= 0 AND due <= ?
                """, deck_id, today) or 0
            else:
                due_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE queue >= 0 AND due <= ?
                """, today) or 0
            return due_count
        except Exception as e:
            print(f"Error in due cards fallback: {e}")
            return 0
    
    def _get_new_cards_fallback(self, deck_id: int = None) -> int:
        """Fallback method to get new cards count"""
        try:
            if deck_id:
                new_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE did = ? AND queue = 0
                """, deck_id) or 0
            else:
                new_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE queue = 0
                """) or 0
            return new_count
        except Exception as e:
            print(f"Error in new cards fallback: {e}")
            return 0
    
    def _get_overdue_cards_count(self, deck_id: int = None) -> int:
        """Get overdue cards count for specific deck"""
        try:
            today = int(datetime.now().timestamp() / 86400)
            
            if deck_id:
                overdue_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE did = ? AND queue >= 0 AND due < ?
                """, deck_id, today) or 0
            else:
                overdue_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards 
                    WHERE queue >= 0 AND due < ?
                """, today) or 0
            return overdue_count
        except Exception as e:
            print(f"Error counting overdue cards: {e}")
            return 0
    
    def _get_total_cards_count(self, deck_id: int = None) -> int:
        """Get total cards count for specific deck"""
        try:
            if deck_id:
                total_count = mw.col.db.scalar("""
                    SELECT COUNT(*) FROM cards WHERE did = ?
                """, deck_id) or 0
            else:
                total_count = mw.col.card_count()
            return total_count
        except Exception as e:
            print(f"Error getting total cards count: {e}")
            return 0
    
    def get_overall_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Calculate overall metrics from recent review history"""
        try:
            # Get all sessions for metrics calculation (not just latest)
            all_sessions = self._get_all_sessions_for_metrics(days_back)
            
            if not all_sessions:
                return {}
            
            return {
                "motivation_trend": self._calculate_motivation_trend(all_sessions),
                "engagement_score": self._calculate_engagement_score(all_sessions),
                "procrastination_indicator": self._calculate_procrastination_indicator(all_sessions),
                "burnout_risk_score": self._calculate_burnout_risk(all_sessions),
                "avg_session_duration": self._calculate_avg_session_duration(all_sessions),
                "total_sessions": len(all_sessions),
                "total_cards_reviewed": sum(s.get('cards_reviewed', 0) for s in all_sessions)
            }
            
        except Exception as e:
            print(f"Error calculating overall metrics: {e}")
            return {}
    
    def _get_all_sessions_for_metrics(self, days_back: int) -> List[Dict[str, Any]]:
        """Get all individual sessions (not merged) for metrics calculation"""
        if not mw.col:
            return []
        
        try:
            # Get cutoff timestamp
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            # Query Anki's review log
            reviews = mw.col.db.all("""
                SELECT id, cid, usn, ease, ivl, lastIvl, factor, time, type
                FROM revlog 
                WHERE id > ?
                ORDER BY id ASC
            """, cutoff_timestamp)
            
            if not reviews:
                return []
            
            # Convert to review objects and group into sessions
            review_objects = self._parse_reviews(reviews)
            sessions = self._group_reviews_into_sessions(review_objects)
            
            # Calculate session metrics (don't merge for overall metrics)
            return [self._calculate_session_metrics(session) for session in sessions]
            
        except Exception as e:
            print(f"Error getting sessions for metrics: {e}")
            return []
    
    def _merge_sessions_by_date_and_deck(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge sessions by date and deck"""
        if not sessions:
            return []
        
        # Group sessions by date and deck
        grouped = {}
        
        for session in sessions:
            date_key = session.get('date', '')
            deck_name = self._get_deck_name_from_session(session)
            key = f"{date_key}_{deck_name}"
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(session)
        
        # Merge sessions for each date/deck combination
        merged_sessions = []
        for sessions_group in grouped.values():
            if len(sessions_group) == 1:
                # Single session, no merging needed
                merged_sessions.append(sessions_group[0])
            else:
                # Multiple sessions, merge them
                merged_session = self._merge_session_group(sessions_group)
                merged_sessions.append(merged_session)
        
        # Sort by date (most recent first)
        merged_sessions.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return merged_sessions
    
    def _get_deck_name_from_session(self, session: Dict[str, Any]) -> str:
        """Extract deck name from session (for now, use 'default' since we don't track deck per review)"""
        # For now, we'll assume all reviews are from the same deck
        # In the future, this could be enhanced to track deck names per review
        return "default"
    
    def _merge_session_group(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple sessions from the same day/deck"""
        if not sessions:
            return {}
        
        if len(sessions) == 1:
            return sessions[0]
        
        # Sort sessions by start time
        sessions.sort(key=lambda x: x.get('session_start', ''))
        
        first_session = sessions[0]
        last_session = sessions[-1]
        
        # Sum values that should be summed
        total_duration = sum(s.get('duration_minutes', 0) for s in sessions)
        total_cards_reviewed = sum(s.get('cards_reviewed', 0) for s in sessions)
        total_correct_reviews = sum(s.get('correct_reviews', 0) for s in sessions)
        total_reviews_again = sum(s.get('reviews_again', 0) for s in sessions)
        total_reviews_hard = sum(s.get('reviews_hard', 0) for s in sessions)
        total_reviews_good = sum(s.get('reviews_good', 0) for s in sessions)
        total_reviews_easy = sum(s.get('reviews_easy', 0) for s in sessions)
        
        # For new cards learned, take the maximum (not sum) to avoid double counting
        # Since we now count unique card IDs, this should be more accurate
        max_new_cards_learned = max(s.get('new_cards_learned', 0) for s in sessions)
        
        # Calculate weighted average for response times
        total_response_time_weighted = 0
        total_cards_for_avg = 0
        
        for session in sessions:
            response_time = session.get('avg_response_time', 0)
            cards_count = session.get('cards_reviewed', 0)
            if response_time > 0 and cards_count > 0:
                total_response_time_weighted += response_time * cards_count
                total_cards_for_avg += cards_count
        
        avg_response_time = (total_response_time_weighted / total_cards_for_avg) if total_cards_for_avg > 0 else 0
        
        # Calculate success rate
        success_rate = (total_correct_reviews / total_cards_reviewed) if total_cards_reviewed > 0 else 0
        
        return {
            "date": first_session.get('date', ''),
            "session_start": first_session.get('session_start', ''),
            "session_end": last_session.get('session_end', ''),
            "duration_minutes": round(total_duration, 1),
            "cards_reviewed": total_cards_reviewed,
            "correct_reviews": total_correct_reviews,
            "success_rate": round(success_rate, 3),
            "avg_response_time": round(avg_response_time, 1),
            "new_cards_learned": max_new_cards_learned,  # Take max instead of sum
            "reviews_again": total_reviews_again,
            "reviews_hard": total_reviews_hard,
            "reviews_good": total_reviews_good,
            "reviews_easy": total_reviews_easy,
            "merged_sessions_count": len(sessions)  # Track how many sessions were merged
        }
    
    def _parse_reviews(self, raw_reviews: List) -> List[Dict[str, Any]]:
        """Parse raw review data from database"""
        reviews = []
        
        for review in raw_reviews:
            review_time = datetime.fromtimestamp(review[0] / 1000)  # Convert from ms
            
            reviews.append({
                "review_time": review_time,
                "card_id": review[1],
                "ease": review[3],  # 1=Again, 2=Hard, 3=Good, 4=Easy
                "response_time": review[7] / 1000.0,  # Convert to seconds
                "review_type": review[8],  # 0=learn, 1=review, 2=relearn, 3=filtered
                "interval": review[4],  # New interval
                "previous_interval": review[5]  # Previous interval
            })
        
        return reviews
    
    def _group_reviews_into_sessions(self, reviews: List[Dict]) -> List[List[Dict]]:
        """Group reviews into sessions based on time gaps"""
        if not reviews:
            return []
        
        sessions = []
        current_session = [reviews[0]]
        
        for i in range(1, len(reviews)):
            current_review = reviews[i]
            previous_review = reviews[i-1]
            
            # Calculate time gap in minutes
            time_gap = (current_review["review_time"] - previous_review["review_time"]).total_seconds() / 60
            
            if time_gap > self.session_gap_minutes:
                # End current session, start new one
                sessions.append(current_session)
                current_session = [current_review]
            else:
                current_session.append(current_review)
        
        # Add the last session
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _calculate_session_metrics(self, session_reviews: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics for a single session"""
        if not session_reviews:
            return {}
        
        # Basic session info
        start_time = session_reviews[0]["review_time"]
        end_time = session_reviews[-1]["review_time"]
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        # Review outcomes
        total_reviews = len(session_reviews)
        correct_reviews = sum(1 for r in session_reviews if r["ease"] >= 3)  # Good or Easy
        
        # Button distribution
        button_counts = {"again": 0, "hard": 0, "good": 0, "easy": 0}
        for review in session_reviews:
            ease = review["ease"]
            if ease == 1:
                button_counts["again"] += 1
            elif ease == 2:
                button_counts["hard"] += 1
            elif ease == 3:
                button_counts["good"] += 1
            elif ease == 4:
                button_counts["easy"] += 1
        
        # Response times
        response_times = [r["response_time"] for r in session_reviews if r["response_time"] > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Count NEW CARDS LEARNED - Fixed logic
        # Count unique cards that were new (review_type 0) and graduated (interval >= 1 day)
        new_cards_graduated = set()
        for review in session_reviews:
            if review["review_type"] == 0 and review["interval"] >= 1:  # New card that graduated
                new_cards_graduated.add(review["card_id"])
        
        new_cards_learned = len(new_cards_graduated)
        
        return {
            "date": start_time.date().isoformat(),
            "session_start": start_time.isoformat(),
            "session_end": end_time.isoformat(),
            "duration_minutes": round(duration_minutes, 1),
            "cards_reviewed": total_reviews,
            "correct_reviews": correct_reviews,
            "success_rate": round(correct_reviews / total_reviews, 3) if total_reviews > 0 else 0,
            "avg_response_time": round(avg_response_time, 1),
            "new_cards_learned": new_cards_learned,
            "reviews_again": button_counts["again"],
            "reviews_hard": button_counts["hard"],
            "reviews_good": button_counts["good"],
            "reviews_easy": button_counts["easy"]
        }
    
    def _calculate_motivation_trend(self, sessions: List[Dict]) -> float:
        """Calculate motivation trend (-1 to 1, based on session frequency and quality)"""
        if len(sessions) < 4:  # Need at least 4 sessions for trend
            return 0.0
        
        # Split sessions into two halves
        mid_point = len(sessions) // 2
        recent_sessions = sessions[mid_point:]
        older_sessions = sessions[:mid_point]
        
        # Compare session frequency
        recent_avg_per_day = len(recent_sessions) / 7 if recent_sessions else 0
        older_avg_per_day = len(older_sessions) / 7 if older_sessions else 0
        
        # Compare session quality (duration and success rate)
        recent_quality = self._calculate_session_quality(recent_sessions)
        older_quality = self._calculate_session_quality(older_sessions)
        
        # Combine frequency and quality trends
        frequency_trend = (recent_avg_per_day - older_avg_per_day) / max(older_avg_per_day, 0.1)
        quality_trend = (recent_quality - older_quality) / max(older_quality, 0.1)
        
        # Weight and normalize to -1 to 1 range
        motivation_trend = (frequency_trend * 0.6 + quality_trend * 0.4) / 2
        return max(-1.0, min(1.0, motivation_trend))
    
    def _calculate_engagement_score(self, sessions: List[Dict]) -> float:
        """Calculate engagement score (0 to 1, based on consistency and session quality)"""
        if not sessions:
            return 0.0
        
        # Session consistency (how regular are study sessions)
        session_dates = set(s["date"] for s in sessions)
        days_with_sessions = len(session_dates)
        consistency_score = min(days_with_sessions / 7, 1.0)  # Normalize to 7 days
        
        # Average session quality
        avg_quality = self._calculate_session_quality(sessions)
        
        # Session completion rate (sessions with reasonable duration)
        complete_sessions = sum(1 for s in sessions if s.get("duration_minutes", 0) >= 5)
        completion_rate = complete_sessions / len(sessions)
        
        # Combine factors
        engagement = (consistency_score * 0.4 + avg_quality * 0.4 + completion_rate * 0.2)
        return round(engagement, 3)
    
    def _calculate_procrastination_indicator(self, sessions: List[Dict]) -> float:
        """Calculate procrastination indicator (0 to 1, higher = more procrastination)"""
        try:
            current_state = self.get_current_deck_state()
            
            # Factor 1: Overdue cards ratio
            total_due = current_state.get("cards_due_today", 0) + current_state.get("cards_overdue", 0)
            overdue_ratio = current_state.get("cards_overdue", 0) / max(total_due, 1)
            
            # Factor 2: Session frequency decline
            if len(sessions) >= 7:
                recent_sessions = len([s for s in sessions[-3:]])  # Last 3 days
                expected_sessions = 3  # Ideally 1 per day
                frequency_deficit = max(0, (expected_sessions - recent_sessions) / expected_sessions)
            else:
                frequency_deficit = 0
            
            # Factor 3: Days since last session
            last_session_date = current_state.get("last_session_date")
            if last_session_date:
                days_since_last = (date.today() - date.fromisoformat(last_session_date)).days
                recency_penalty = min(days_since_last / 7, 1.0)  # Normalize to week
            else:
                recency_penalty = 1.0
            
            # Combine factors
            procrastination = (overdue_ratio * 0.4 + frequency_deficit * 0.3 + recency_penalty * 0.3)
            return round(min(procrastination, 1.0), 3)
            
        except Exception as e:
            print(f"Error calculating procrastination indicator: {e}")
            return 0.0
    
    def _calculate_burnout_risk(self, sessions: List[Dict]) -> float:
        """Calculate burnout risk (0 to 1, based on declining performance + high workload)"""
        if len(sessions) < 5:
            return 0.0
        
        # Factor 1: Performance decline
        recent_sessions = sessions[-3:]
        older_sessions = sessions[-6:-3] if len(sessions) >= 6 else sessions[:-3]
        
        recent_success = sum(s.get("success_rate", 0) for s in recent_sessions) / len(recent_sessions)
        older_success = sum(s.get("success_rate", 0) for s in older_sessions) / len(older_sessions) if older_sessions else recent_success
        
        performance_decline = max(0, older_success - recent_success)
        
        # Factor 2: Response time increase
        recent_response_time = sum(s.get("avg_response_time", 0) for s in recent_sessions) / len(recent_sessions)
        older_response_time = sum(s.get("avg_response_time", 0) for s in older_sessions) / len(older_sessions) if older_sessions else recent_response_time
        
        response_time_increase = max(0, (recent_response_time - older_response_time) / max(older_response_time, 1))
        
        # Factor 3: High workload
        current_state = self.get_current_deck_state()
        total_due = current_state.get("cards_due_today", 0) + current_state.get("cards_overdue", 0)
        workload_pressure = min(total_due / 100, 1.0)  # Normalize to 100 cards
        
        # Combine factors
        burnout_risk = (performance_decline * 0.4 + response_time_increase * 0.3 + workload_pressure * 0.3)
        return round(min(burnout_risk, 1.0), 3)
    
    def _calculate_session_quality(self, sessions: List[Dict]) -> float:
        """Calculate average quality score for sessions"""
        if not sessions:
            return 0.0
        
        quality_scores = []
        for session in sessions:
            success_rate = session.get("success_rate", 0)
            duration = session.get("duration_minutes", 0)
            cards_reviewed = session.get("cards_reviewed", 0)
            
            # Quality based on success rate, reasonable duration, and card count
            duration_score = min(duration / 20, 1.0)  # Normalize to 20 minutes
            volume_score = min(cards_reviewed / 30, 1.0)  # Normalize to 30 cards
            
            quality = (success_rate * 0.5 + duration_score * 0.25 + volume_score * 0.25)
            quality_scores.append(quality)
        
        return sum(quality_scores) / len(quality_scores)
    
    def _calculate_avg_session_duration(self, sessions: List[Dict]) -> float:
        """Calculate average session duration"""
        if not sessions:
            return 0.0
        
        durations = [s.get("duration_minutes", 0) for s in sessions]
        return round(sum(durations) / len(durations), 1)
    
    def _calculate_current_streak(self) -> int:
        """Calculate current study streak in days"""
        if not mw.col:
            return 0
        
        try:
            # Get dates with reviews in the last 30 days
            cutoff_timestamp = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            
            review_dates = mw.col.db.list("""
                SELECT DISTINCT date(id/1000, 'unixepoch', 'localtime') as review_date
                FROM revlog 
                WHERE id > ?
                ORDER BY review_date DESC
            """, cutoff_timestamp)
            
            if not review_dates:
                return 0
            
            # Count consecutive days from today backwards
            current_date = date.today()
            streak = 0
            
            for review_date_str in review_dates:
                review_date = date.fromisoformat(review_date_str)
                
                if review_date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                elif review_date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            print(f"Error calculating current streak: {e}")
            return 0
    
    def _get_last_session_date(self) -> Optional[str]:
        """Get the date of the last study session"""
        if not mw.col:
            return None
        
        try:
            last_review = mw.col.db.scalar("""
                SELECT MAX(id) FROM revlog
            """)
            
            if last_review:
                last_date = datetime.fromtimestamp(last_review / 1000).date()
                return last_date.isoformat()
            
            return None
            
        except Exception as e:
            print(f"Error getting last session date: {e}")
            return None