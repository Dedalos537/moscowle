package com.example.moscowle.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod; // Import HttpMethod
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable()) 
            .authorizeHttpRequests(authorize -> authorize
                .requestMatchers(new AntPathRequestMatcher("/img/**")).permitAll()
                .requestMatchers(new AntPathRequestMatcher("/css/**")).permitAll() 
                .requestMatchers(new AntPathRequestMatcher("/js/**")).permitAll()   
                .requestMatchers(new AntPathRequestMatcher("/favicon.ico")).permitAll() 

                .requestMatchers(new AntPathRequestMatcher("/api/login", HttpMethod.POST.name())).permitAll()

                .requestMatchers(new AntPathRequestMatcher("/api/registro", HttpMethod.POST.name())).permitAll()

                .requestMatchers(new AntPathRequestMatcher("/api/registro", HttpMethod.GET.name())).hasRole("ADMIN")

                .requestMatchers(new AntPathRequestMatcher("/api/registro/**", HttpMethod.PUT.name())).hasRole("ADMIN")

                .anyRequest().authenticated()
            )
      
            ;

        return http.build();
    }


}