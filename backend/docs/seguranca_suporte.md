# Manual de Segurança — Zero Trust & Suporte
O acesso ao sistema utiliza autenticação JWT com refresh token rotativo e controle de permissões por perfil (STUDENT, SUPPORT, ADMIN).
O agente SmartCampus AI atua via servidor MCP com menor privilégio: nunca acessa o banco diretamente e valida o user_id e a role da sessão autenticada.
Dúvidas não cobertas pelo regulamento devem ser encaminhadas ao perfil SUPPORT.
