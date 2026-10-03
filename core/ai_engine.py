"""
AI Recommendation Engine for SportsHub (SRS FR-5.1 to FR-5.5, FR-6.8)
Implements interpretable, multi-factor weighted scoring and role-balanced lineup optimization.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any

class AIRecEngine:
    # Default weighting factors (SRS Section 1.4, 2.5)
    WEIGHT_FITNESS = 0.35
    WEIGHT_FORM = 0.30
    WEIGHT_GROUND_AFFINITY = 0.15
    WEIGHT_WEATHER_AFFINITY = 0.10
    WEIGHT_EXPERIENCE_STAMINA = 0.10

    INJURY_MULTIPLIERS = {
        'FIT': 1.0,
        'MINOR_ISSUE': 0.65,
        'INJURED': 0.05
    }

    FORMATION_REQUIREMENTS = {
        'Football': {
            'Goalkeeper': 1,
            'Defender': 4,
            'Midfielder': 3,
            'Forward': 3
        },
        'Cricket': {
            'Wicketkeeper': 1,
            'Batsman': 4,
            'All-Rounder': 3,
            'Bowler': 3
        },
        'Default': {
            'Goalkeeper': 1,
            'Defender': 4,
            'Midfielder': 3,
            'Forward': 3
        }
    }

    @classmethod
    def calculate_player_score(
        cls,
        player_data: Dict[str, Any],
        match_ground: str = 'Grass',
        match_weather: str = 'Sunny'
    ) -> Dict[str, Any]:
        """
        Computes an interpretable composite suitability score for a single player.
        """
        # 1. Normalized Fitness (0 to 100)
        raw_fitness = float(player_data.get('fitness_score', 85))
        norm_fitness = min(max(raw_fitness / 100.0, 0.0), 1.0)

        # 2. Normalized Recent Form (1.0 to 10.0)
        raw_form = float(player_data.get('recent_form', 7.0))
        norm_form = min(max(raw_form / 10.0, 0.0), 1.0)

        # 3. Ground Affinity
        pref_ground = player_data.get('preferred_ground', 'Any')
        if pref_ground == 'Any' or pref_ground == match_ground:
            ground_score = 1.0
        elif pref_ground == 'Grass' and match_ground in ['Turf', 'Indoor']:
            ground_score = 0.75
        elif pref_ground == 'Turf' and match_ground in ['Grass', 'Clay']:
            ground_score = 0.75
        else:
            ground_score = 0.60

        # 4. Weather Affinity
        pref_weather = player_data.get('preferred_weather', 'Any')
        if pref_weather == 'Any' or pref_weather == match_weather:
            weather_score = 1.0
        elif match_weather in ['Rainy', 'Humid'] and pref_weather == 'Sunny':
            weather_score = 0.70
        else:
            weather_score = 0.85

        # 5. Stamina / Pace combined rating
        stamina = float(player_data.get('stamina_rating', 80.0)) / 100.0
        pace = float(player_data.get('pace_rating', 80.0)) / 100.0
        experience_score = (stamina * 0.6) + (pace * 0.4)

        # Base Weighted Composite Score
        base_score = (
            (cls.WEIGHT_FITNESS * norm_fitness) +
            (cls.WEIGHT_FORM * norm_form) +
            (cls.WEIGHT_GROUND_AFFINITY * ground_score) +
            (cls.WEIGHT_WEATHER_AFFINITY * weather_score) +
            (cls.WEIGHT_EXPERIENCE_STAMINA * experience_score)
        )

        # Apply Injury Multiplier
        injury_status = player_data.get('injury_status', 'FIT')
        multiplier = cls.INJURY_MULTIPLIERS.get(injury_status, 1.0)
        final_suitability = base_score * multiplier * 100.0

        # Formulate human-readable decision reasons
        reasons = []
        if raw_fitness >= 90:
            reasons.append(f"Peak Match Fitness ({int(raw_fitness)}%)")
        elif raw_fitness < 70:
            reasons.append(f"Reduced Fitness ({int(raw_fitness)}%)")

        if raw_form >= 8.5:
            reasons.append(f"In-Form Momentum ({raw_form:.1f}/10)")
        elif raw_form < 6.0:
            reasons.append(f"Sluggish Form ({raw_form:.1f}/10)")

        if ground_score == 1.0 and pref_ground != 'Any':
            reasons.append(f"Adept on {match_ground}")
        if weather_score == 1.0 and pref_weather != 'Any':
            reasons.append(f"Optimal for {match_weather} Weather")

        if injury_status == 'MINOR_ISSUE':
            reasons.append("Caution: Carrying Minor Knock")
        elif injury_status == 'INJURED':
            reasons.append("Warning: Player Sidelined with Injury")

        return {
            'player_id': player_data.get('id'),
            'name': player_data.get('name'),
            'role': player_data.get('role'),
            'jersey_number': player_data.get('jersey_number'),
            'suitability_score': round(final_suitability, 1),
            'norm_fitness': round(norm_fitness * 100, 1),
            'norm_form': round(norm_form * 10, 1),
            'ground_affinity_pct': round(ground_score * 100, 1),
            'weather_affinity_pct': round(weather_score * 100, 1),
            'injury_status': injury_status,
            'reasons': reasons,
            'is_available': player_data.get('is_available_for_matchday', True)
        }

    @classmethod
    def recommend_lineup(
        cls,
        players: List[Any],
        sport_name: str = 'Football',
        match_ground: str = 'Grass',
        match_weather: str = 'Sunny'
    ) -> Dict[str, Any]:
        """
        Executes end-to-end AI lineup recommendation for a team roster.
        """
        if not players:
            return {
                'starting_xi': [],
                'bench': [],
                'overall_confidence': 0.0,
                'factors': {},
                'top_picks': []
            }

        # Convert queryset or list of dicts to scored list
        scored_players = []
        for p in players:
            if hasattr(p, 'name'):
                p_data = {
                    'id': p.id,
                    'name': p.name,
                    'role': p.role,
                    'jersey_number': p.jersey_number,
                    'fitness_score': p.fitness_score,
                    'injury_status': p.injury_status,
                    'recent_form': p.recent_form,
                    'stamina_rating': p.stamina_rating,
                    'pace_rating': p.pace_rating,
                    'preferred_ground': p.preferred_ground,
                    'preferred_weather': p.preferred_weather,
                    'is_available_for_matchday': p.is_available_for_matchday
                }
            else:
                p_data = p

            score_res = cls.calculate_player_score(p_data, match_ground, match_weather)
            scored_players.append(score_res)

        # Sort all players by suitability score descending
        scored_players.sort(key=lambda x: x['suitability_score'], reverse=True)
        available_players = [p for p in scored_players if p['is_available'] and p['injury_status'] != 'INJURED']

        # Role requirements
        reqs = cls.FORMATION_REQUIREMENTS.get(sport_name, cls.FORMATION_REQUIREMENTS['Default'])
        
        starting_lineup = []
        remaining_pool = list(available_players)

        # Pick best candidates for each positional role
        for role, needed_count in reqs.items():
            role_candidates = [p for p in remaining_pool if p['role'].lower() == role.lower() and p['is_available']]
            # If not enough exact matches, fallback to closest
            if len(role_candidates) < needed_count:
                extra_needed = needed_count - len(role_candidates)
                role_candidates += [p for p in remaining_pool if p not in role_candidates and p['is_available']][:extra_needed]

            picked = role_candidates[:needed_count]
            for p in picked:
                starting_lineup.append(p)
                if p in remaining_pool:
                    remaining_pool.remove(p)

        # If starting lineup has fewer than 11 (e.g. 11 total needed), fill with best available
        target_size = sum(reqs.values())
        while len(starting_lineup) < min(target_size, len(scored_players)) and remaining_pool:
            next_best = remaining_pool.pop(0)
            starting_lineup.append(next_best)

        # Remaining players become the bench
        bench = remaining_pool

        # Calculate overall tactical confidence score
        if starting_lineup:
            avg_score = np.mean([p['suitability_score'] for p in starting_lineup])
            # Penalty if starting players have minor issues
            penalties = sum(10 for p in starting_lineup if p['injury_status'] != 'FIT')
            confidence = min(max(avg_score - (penalties * 0.5), 40.0), 99.5)
        else:
            confidence = 50.0

        factors_summary = {
            'ground_type': match_ground,
            'weather_condition': match_weather,
            'weights': {
                'fitness': cls.WEIGHT_FITNESS,
                'form': cls.WEIGHT_FORM,
                'ground': cls.WEIGHT_GROUND_AFFINITY,
                'weather': cls.WEIGHT_WEATHER_AFFINITY,
                'stamina': cls.WEIGHT_EXPERIENCE_STAMINA
            },
            'starting_xi_count': len(starting_lineup),
            'bench_count': len(bench),
            'avg_lineup_fitness': round(float(np.mean([p['norm_fitness'] for p in starting_lineup])) if starting_lineup else 0.0, 1),
            'avg_lineup_form': round(float(np.mean([p['norm_form'] for p in starting_lineup])) if starting_lineup else 0.0, 1)
        }

        return {
            'starting_xi': starting_lineup,
            'bench': bench,
            'overall_confidence': round(float(confidence), 1),
            'factors': factors_summary,
            'all_ranked': scored_players
        }
