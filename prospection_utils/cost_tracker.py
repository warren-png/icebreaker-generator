"""
Tracker de coûts pour l'API Claude
Permet de monitorer les dépenses en temps réel
Version: 1.0
"""

from datetime import datetime
import json
import os

# Prix Claude Sonnet 4 (au 21/01/2026 - vérifier les prix réels sur console.anthropic.com)
PRICE_INPUT_TOKEN = 0.000003   # $3 per 1M tokens
PRICE_OUTPUT_TOKEN = 0.000015  # $15 per 1M tokens

class ClaudeUsageTracker:
    """Tracker pour suivre l'utilisation et les coûts de l'API Claude"""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls = []
        self.session_start = datetime.now()
    
    def track(self, usage, function_name):
        """
        Enregistre l'utilisation d'un appel API
        
        Args:
            usage: Objet usage de Claude (message.usage)
            function_name (str): Nom de la fonction appelante
        """
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        
        # Calculer le coût de cet appel
        call_cost = (usage.input_tokens * PRICE_INPUT_TOKEN) + (usage.output_tokens * PRICE_OUTPUT_TOKEN)
        
        call_data = {
            'timestamp': datetime.now().isoformat(),
            'function': function_name,
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens,
            'total_tokens': usage.input_tokens + usage.output_tokens,
            'cost_usd': round(call_cost, 4)
        }
        
        self.calls.append(call_data)
        
        # Afficher dans la console
        print(f"💰 [{function_name}] Tokens: {usage.input_tokens}→{usage.output_tokens} | Coût: ${call_cost:.4f}")
    
    def get_total_cost(self):
        """Retourne le coût total de la session"""
        total = (self.total_input_tokens * PRICE_INPUT_TOKEN) + (self.total_output_tokens * PRICE_OUTPUT_TOKEN)
        return round(total, 4)
    
    def get_summary(self):
        """Retourne un résumé de l'utilisation"""
        duration = (datetime.now() - self.session_start).total_seconds()
        
        return {
            'session_duration_seconds': round(duration, 2),
            'total_calls': len(self.calls),
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_cost_usd': self.get_total_cost()
        }
    
    def print_summary(self):
        """Affiche un résumé formaté"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 RÉSUMÉ UTILISATION CLAUDE")
        print("="*60)
        print(f"⏱️  Durée session       : {summary['session_duration_seconds']}s")
        print(f"📞 Nombre d'appels     : {summary['total_calls']}")
        print(f"📥 Tokens entrée       : {summary['total_input_tokens']:,}")
        print(f"📤 Tokens sortie       : {summary['total_output_tokens']:,}")
        print(f"📊 Tokens total        : {summary['total_tokens']:,}")
        print(f"💵 COÛT TOTAL          : ${summary['total_cost_usd']}")
        print("="*60 + "\n")
    
    def save_to_file(self, filename=None):
        """Sauvegarde les stats dans un fichier JSON"""
        if filename is None:
            filename = f'logs/claude_usage_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # Créer le dossier logs s'il n'existe pas
        os.makedirs('logs', exist_ok=True)
        
        data = {
            'summary': self.get_summary(),
            'calls': self.calls
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Stats sauvegardées : {filename}")

# Instance globale du tracker
tracker = ClaudeUsageTracker()
