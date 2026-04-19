package com.sms.sms.course.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Table(name = "t_course_catalog")
public class CourseCatalog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "course_code", unique = true, nullable = false, length = 20)
    private String courseCode;

    @Column(nullable = false, length = 100)
    private String courseName;

    @Column(precision = 3, scale = 1)
    private BigDecimal credit;

    @Column(name = "capacity", nullable = false)
    private Integer capacity;

    @Column(name = "type")
    private Integer type; // 1:必修 2:选修

    @Column(columnDefinition = "JSONB")
    private String prerequisites;

    @Column(columnDefinition = "JSONB")
    private String semesterSchedule;

    @Version
    private Integer version;

    @Column(name = "created_at", updatable = false)
    private java.time.LocalDateTime createdAt;

    @Column(name = "updated_at")
    private java.time.LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = java.time.LocalDateTime.now();
        updatedAt = java.time.LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = java.time.LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getCourseCode() { return courseCode; }
    public void setCourseCode(String courseCode) { this.courseCode = courseCode; }
    public String getCourseName() { return courseName; }
    public void setCourseName(String courseName) { this.courseName = courseName; }
    public BigDecimal getCredit() { return credit; }
    public void setCredit(BigDecimal credit) { this.credit = credit; }
    public Integer getCapacity() { return capacity; }
    public void setCapacity(Integer capacity) { this.capacity = capacity; }
    public Integer getType() { return type; }
    public void setType(Integer type) { this.type = type; }
    public String getPrerequisites() { return prerequisites; }
    public void setPrerequisites(String prerequisites) { this.prerequisites = prerequisites; }
    public String getSemesterSchedule() { return semesterSchedule; }
    public void setSemesterSchedule(String semesterSchedule) { this.semesterSchedule = semesterSchedule; }
    public Integer getVersion() { return version; }
    public void setVersion(Integer version) { this.version = version; }
    public java.time.LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(java.time.LocalDateTime createdAt) { this.createdAt = createdAt; }
    public java.time.LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(java.time.LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}