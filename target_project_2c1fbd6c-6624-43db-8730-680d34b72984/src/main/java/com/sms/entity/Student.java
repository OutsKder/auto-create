package com.sms.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Entity
@Table(name = "t_student_profile")
@Data
public class Student {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "student_no", unique = true, nullable = false, length = 20)
    private String studentNo;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(length = 18)
    private String idCard;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.ACTIVE;

    @Column(name = "major_code", length = 20)
    private String majorCode;

    @Column(name = "entry_date")
    private LocalDateTime entryDate;

    @Version
    private Integer version;

    @Column(name = "created_at", updatable = false)
    @Temporal(TemporalType.TIMESTAMP)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    @Temporal(TemporalType.TIMESTAMP)
    private LocalDateTime updatedAt;

    public enum Status {
        ACTIVE, SUSPENDED, GRADUATED, WITHDRAWN
    }
}