package com.example.moscowle.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.example.moscowle.models.Contactanos;

@Repository
public interface ContactanosRepository extends JpaRepository<Contactanos, Long>{

}
