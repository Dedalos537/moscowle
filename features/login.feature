Feature: Inicio de sesión
  Como usuario registrado
  Quiero iniciar sesión en el sistema
  Para acceder a mis sesiones y reportes

  Background:
    Given un usuario registrado con email "test@example.com" y password "password123"

  Scenario: Login exitoso con credenciales válidas
    When envía credenciales correctas a /api/login
    Then recibe status 200 y token CSRF
    And el usuario está autenticado

  Scenario: Login fallido por credenciales incorrectas
    When envía credenciales incorrectas a /api/login
    Then recibe status 401

  Scenario: Login fallido por campos vacíos
    Given un formulario de login vacío
    When envía email y password vacíos a /api/login
    Then recibe status 400
