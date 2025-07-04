package com.example.moscowle.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfigurationSource;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Autowired
    private CorsConfigurationSource corsConfigurationSource;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(cors -> cors.configurationSource(corsConfigurationSource)) // Habilitar CORS
            .csrf(csrf -> csrf.disable()) 
            .authorizeHttpRequests(authorize -> authorize
                // Recursos estáticos
                .requestMatchers("/img/**", "/css/**", "/js/**", "/favicon.ico").permitAll()
                
                // Endpoints públicos
                .requestMatchers(HttpMethod.POST, "/api/login").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/registro").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/logout").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/contactanos").permitAll()
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll() // Para CORS preflight
                
                // Endpoints de administrador
                .requestMatchers(HttpMethod.GET, "/api/registro").hasRole("ADMIN")
                .requestMatchers(HttpMethod.PUT, "/api/registro/**").hasRole("ADMIN")
                
                // Resto de endpoints requieren autenticación
                .anyRequest().authenticated()
            )
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS));

        return http.build();
    }

    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}