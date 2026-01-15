SET FOREIGN_KEY_CHECKS = 0;

-- Drop all tables in correct order
DROP TABLE IF EXISTS sms_resource_downloads;
DROP TABLE IF EXISTS sms_resources;
DROP TABLE IF EXISTS sms_discussion_replies;
DROP TABLE IF EXISTS sms_discussions;
DROP TABLE IF EXISTS sms_quiz_submissions;
DROP TABLE IF EXISTS sms_quiz_questions;
DROP TABLE IF EXISTS sms_quizzes;
DROP TABLE IF EXISTS sms_class_attendance;
DROP TABLE IF EXISTS sms_online_classes;
DROP TABLE IF EXISTS sms_assignment_submissions;
DROP TABLE IF EXISTS sms_assignments;
DROP TABLE IF EXISTS sms_course_enrollments;
DROP TABLE IF EXISTS sms_course_materials;
DROP TABLE IF EXISTS sms_courses;
DROP TABLE IF EXISTS sms_announcements;
DROP TABLE IF EXISTS sms_events;
DROP TABLE IF EXISTS sms_notifications;
DROP TABLE IF EXISTS sms_parent_students;
DROP TABLE IF EXISTS sms_grades;
DROP TABLE IF EXISTS sms_messages;
DROP TABLE IF EXISTS sms_attendance;
DROP TABLE IF EXISTS sms_students;
DROP TABLE IF EXISTS sms_teacher;
DROP TABLE IF EXISTS sms_classes;
DROP TABLE IF EXISTS sms_section;
DROP TABLE IF EXISTS sms_subjects;
DROP TABLE IF EXISTS sms_user;

SET FOREIGN_KEY_CHECKS = 1;

-- ==================== CORE TABLES ====================

-- Users table (for authentication)
CREATE TABLE `sms_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(50) NOT NULL,
  `last_name` varchar(50) NOT NULL,
  `email` varchar(50) NOT NULL,
  `password` varchar(100) NOT NULL,
  `gender` enum('male','female','other') DEFAULT 'male',
  `mobile` varchar(20) DEFAULT NULL,
  `designation` varchar(100) DEFAULT NULL,
  `image` varchar(250) DEFAULT NULL,
  `type` enum('administrator','teacher','student','parent','general') DEFAULT 'general',
  `status` enum('active','pending','deleted','') DEFAULT 'active',
  `authtoken` varchar(250) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sections table
CREATE TABLE `sms_section` (
  `section_id` int(11) NOT NULL AUTO_INCREMENT,
  `section` varchar(255) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`section_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Subjects table
CREATE TABLE `sms_subjects` (
  `subject_id` int(11) NOT NULL AUTO_INCREMENT,
  `subject` varchar(255) NOT NULL,
  `type` varchar(255) NOT NULL,
  `code` int(11) NOT NULL,
  `description` text,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`subject_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Teachers table
CREATE TABLE `sms_teacher` (
  `teacher_id` int(11) NOT NULL AUTO_INCREMENT,
  `teacher` varchar(255) NOT NULL,
  `subject_id` int(11) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `qualification` varchar(255) DEFAULT NULL,
  `experience` varchar(100) DEFAULT NULL,
  `specialization` text,
  `joining_date` date DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`teacher_id`),
  KEY `subject_id` (`subject_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `sms_teacher_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `sms_subjects` (`subject_id`) ON DELETE SET NULL,
  CONSTRAINT `sms_teacher_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `sms_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Classes table
CREATE TABLE `sms_classes` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(40) NOT NULL,
  `section` int(11) NOT NULL,
  `teacher_id` int(11) DEFAULT NULL,
  `room_number` varchar(20) DEFAULT NULL,
  `academic_year` year DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `section` (`section`),
  KEY `teacher_id` (`teacher_id`),
  CONSTRAINT `sms_classes_ibfk_1` FOREIGN KEY (`section`) REFERENCES `sms_section` (`section_id`),
  CONSTRAINT `sms_classes_ibfk_2` FOREIGN KEY (`teacher_id`) REFERENCES `sms_teacher` (`teacher_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Students table
CREATE TABLE `sms_students` (
  `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `gender` varchar(10) NOT NULL,
  `dob` date DEFAULT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `mobile` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `current_address` text,
  `permanent_address` text,
  `father_name` varchar(100) DEFAULT NULL,
  `father_mobile` varchar(20) DEFAULT NULL,
  `father_occupation` varchar(100) DEFAULT NULL,
  `mother_name` varchar(100) DEFAULT NULL,
  `mother_mobile` varchar(20) DEFAULT NULL,
  `mother_occupation` varchar(100) DEFAULT NULL,
  `admission_no` varchar(50) NOT NULL,
  `roll_no` varchar(50) NOT NULL,
  `class` int(10) UNSIGNED NOT NULL,
  `section` int(11) NOT NULL,
  `blood_group` varchar(5) DEFAULT NULL,
  `nationality` varchar(50) DEFAULT NULL,
  `religion` varchar(50) DEFAULT NULL,
  `admission_date` date NOT NULL,
  `academic_year` year NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `admission_no` (`admission_no`),
  UNIQUE KEY `email` (`email`),
  KEY `class` (`class`),
  KEY `section` (`section`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `sms_students_ibfk_1` FOREIGN KEY (`class`) REFERENCES `sms_classes` (`id`),
  CONSTRAINT `sms_students_ibfk_2` FOREIGN KEY (`section`) REFERENCES `sms_section` (`section_id`),
  CONSTRAINT `sms_students_ibfk_3` FOREIGN KEY (`user_id`) REFERENCES `sms_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Attendance table
CREATE TABLE `sms_attendance` (
  `attendance_id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(10) UNSIGNED NOT NULL,
  `class_id` int(10) UNSIGNED NOT NULL,
  `section_id` int(11) NOT NULL,
  `attendance_status` enum('present','absent','late','excused') DEFAULT 'present',
  `attendance_date` date NOT NULL,
  `remarks` text,
  `recorded_by` int(11) DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attendance_id`),
  UNIQUE KEY `unique_attendance` (`student_id`, `attendance_date`),
  KEY `student_id` (`student_id`),
  KEY `class_id` (`class_id`),
  KEY `section_id` (`section_id`),
  KEY `recorded_by` (`recorded_by`),
  CONSTRAINT `sms_attendance_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `sms_attendance_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `sms_classes` (`id`),
  CONSTRAINT `sms_attendance_ibfk_3` FOREIGN KEY (`section_id`) REFERENCES `sms_section` (`section_id`),
  CONSTRAINT `sms_attendance_ibfk_4` FOREIGN KEY (`recorded_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== LMS TABLES ====================

-- Courses/Modules
CREATE TABLE `sms_courses` (
  `course_id` int(11) NOT NULL AUTO_INCREMENT,
  `course_name` varchar(200) NOT NULL,
  `course_code` varchar(50) NOT NULL,
  `description` text,
  `teacher_id` int(11) DEFAULT NULL,
  `class_id` int(10) UNSIGNED DEFAULT NULL,
  `credit_hours` int(3) DEFAULT 3,
  `semester` varchar(50) DEFAULT NULL,
  `status` enum('active','inactive','archived') DEFAULT 'active',
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`course_id`),
  UNIQUE KEY `course_code` (`course_code`),
  KEY `teacher_id` (`teacher_id`),
  KEY `class_id` (`class_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_courses_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `sms_teacher` (`teacher_id`),
  CONSTRAINT `sms_courses_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `sms_classes` (`id`),
  CONSTRAINT `sms_courses_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Course enrollments
CREATE TABLE `sms_course_enrollments` (
  `enrollment_id` int(11) NOT NULL AUTO_INCREMENT,
  `course_id` int(11) NOT NULL,
  `student_id` int(10) UNSIGNED NOT NULL,
  `enrolled_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `status` enum('active','completed','dropped','pending') DEFAULT 'active',
  `grade` varchar(5) DEFAULT NULL,
  `grade_points` decimal(3,2) DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`enrollment_id`),
  UNIQUE KEY `unique_enrollment` (`course_id`, `student_id`),
  KEY `course_id` (`course_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `sms_course_enrollments_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_course_enrollments_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Course materials
CREATE TABLE `sms_course_materials` (
  `material_id` int(11) NOT NULL AUTO_INCREMENT,
  `course_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `material_type` enum('lecture','reading','exercise','video','assignment','other') DEFAULT 'lecture',
  `file_path` varchar(500) DEFAULT NULL,
  `file_size` varchar(50) DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `week_number` int(3) DEFAULT NULL,
  `topic` varchar(255) DEFAULT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`material_id`),
  KEY `course_id` (`course_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_course_materials_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_course_materials_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Assignments
CREATE TABLE `sms_assignments` (
  `assignment_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `course_id` int(11) NOT NULL,
  `due_date` datetime NOT NULL,
  `max_marks` decimal(5,2) DEFAULT 100.00,
  `weightage` decimal(5,2) DEFAULT 10.00,
  `assignment_type` enum('individual','group','quiz','project') DEFAULT 'individual',
  `instructions` text,
  `attachment_path` varchar(500) DEFAULT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`assignment_id`),
  KEY `course_id` (`course_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_assignments_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_assignments_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Assignment submissions
CREATE TABLE `sms_assignment_submissions` (
  `submission_id` int(11) NOT NULL AUTO_INCREMENT,
  `assignment_id` int(11) NOT NULL,
  `student_id` int(10) UNSIGNED NOT NULL,
  `submission_text` text,
  `file_path` varchar(500) DEFAULT NULL,
  `file_size` varchar(50) DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `marks_obtained` decimal(5,2) DEFAULT NULL,
  `feedback` text,
  `submission_date` timestamp DEFAULT CURRENT_TIMESTAMP,
  `graded_at` timestamp NULL DEFAULT NULL,
  `graded_by` int(11) DEFAULT NULL,
  `status` enum('submitted','graded','late','resubmitted') DEFAULT 'submitted',
  PRIMARY KEY (`submission_id`),
  UNIQUE KEY `unique_submission` (`assignment_id`, `student_id`),
  KEY `assignment_id` (`assignment_id`),
  KEY `student_id` (`student_id`),
  KEY `graded_by` (`graded_by`),
  CONSTRAINT `sms_assignment_submissions_ibfk_1` FOREIGN KEY (`assignment_id`) REFERENCES `sms_assignments` (`assignment_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_assignment_submissions_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `sms_assignment_submissions_ibfk_3` FOREIGN KEY (`graded_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Announcements
CREATE TABLE `sms_announcements` (
  `announcement_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `content` text NOT NULL,
  `announcement_type` enum('school','course','department','event','emergency') DEFAULT 'school',
  `course_id` int(11) DEFAULT NULL,
  `target_audience` enum('all','students','teachers','parents','specific_class') DEFAULT 'all',
  `class_id` int(10) UNSIGNED DEFAULT NULL,
  `priority` enum('low','medium','high','urgent') DEFAULT 'medium',
  `expiry_date` date DEFAULT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`announcement_id`),
  KEY `course_id` (`course_id`),
  KEY `class_id` (`class_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_announcements_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_announcements_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `sms_classes` (`id`),
  CONSTRAINT `sms_announcements_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Online classes
CREATE TABLE `sms_online_classes` (
  `class_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `course_id` int(11) NOT NULL,
  `meeting_link` varchar(500) NOT NULL,
  `meeting_id` varchar(100) DEFAULT NULL,
  `meeting_password` varchar(100) DEFAULT NULL,
  `schedule_time` datetime NOT NULL,
  `duration` int(4) DEFAULT 60,
  `platform` enum('zoom','google_meet','microsoft_teams','other') DEFAULT 'google_meet',
  `recording_link` varchar(500) DEFAULT NULL,
  `status` enum('scheduled','ongoing','completed','cancelled') DEFAULT 'scheduled',
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`class_id`),
  KEY `course_id` (`course_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_online_classes_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_online_classes_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Class attendance
CREATE TABLE `sms_class_attendance` (
  `attendance_id` int(11) NOT NULL AUTO_INCREMENT,
  `class_id` int(11) NOT NULL,
  `student_id` int(10) UNSIGNED NOT NULL,
  `attended` tinyint(1) DEFAULT 0,
  `joined_at` timestamp NULL DEFAULT NULL,
  `left_at` timestamp NULL DEFAULT NULL,
  `duration` int(4) DEFAULT 0,
  `attended_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`attendance_id`),
  UNIQUE KEY `unique_class_attendance` (`class_id`, `student_id`),
  KEY `class_id` (`class_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `sms_class_attendance_ibfk_1` FOREIGN KEY (`class_id`) REFERENCES `sms_online_classes` (`class_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_class_attendance_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Quizzes
CREATE TABLE `sms_quizzes` (
  `quiz_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `course_id` int(11) NOT NULL,
  `duration` int(4) DEFAULT 30,
  `total_questions` int(3) DEFAULT 10,
  `passing_percentage` decimal(5,2) DEFAULT 60.00,
  `max_attempts` int(2) DEFAULT 1,
  `shuffle_questions` tinyint(1) DEFAULT 0,
  `shuffle_options` tinyint(1) DEFAULT 0,
  `show_result` tinyint(1) DEFAULT 1,
  `start_date` datetime NOT NULL,
  `end_date` datetime NOT NULL,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`quiz_id`),
  KEY `course_id` (`course_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_quizzes_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_quizzes_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Quiz questions
CREATE TABLE `sms_quiz_questions` (
  `question_id` int(11) NOT NULL AUTO_INCREMENT,
  `quiz_id` int(11) NOT NULL,
  `question` text NOT NULL,
  `question_type` enum('multiple_choice','true_false','short_answer','essay') DEFAULT 'multiple_choice',
  `option_a` varchar(500) DEFAULT NULL,
  `option_b` varchar(500) DEFAULT NULL,
  `option_c` varchar(500) DEFAULT NULL,
  `option_d` varchar(500) DEFAULT NULL,
  `option_e` varchar(500) DEFAULT NULL,
  `correct_answer` varchar(10) DEFAULT NULL,
  `marks` decimal(5,2) DEFAULT 1.00,
  `explanation` text,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`question_id`),
  KEY `quiz_id` (`quiz_id`),
  CONSTRAINT `sms_quiz_questions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `sms_quizzes` (`quiz_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Quiz submissions
CREATE TABLE `sms_quiz_submissions` (
  `submission_id` int(11) NOT NULL AUTO_INCREMENT,
  `quiz_id` int(11) NOT NULL,
  `student_id` int(10) UNSIGNED NOT NULL,
  `attempt_number` int(2) DEFAULT 1,
  `score` decimal(5,2) DEFAULT 0.00,
  `percentage` decimal(5,2) DEFAULT 0.00,
  `answers_json` text,
  `time_taken` int(6) DEFAULT 0,
  `start_time` timestamp NULL DEFAULT NULL,
  `end_time` timestamp NULL DEFAULT NULL,
  `status` enum('in_progress','submitted','graded','expired') DEFAULT 'submitted',
  `attempt_date` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`submission_id`),
  UNIQUE KEY `unique_quiz_attempt` (`quiz_id`, `student_id`, `attempt_number`),
  KEY `quiz_id` (`quiz_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `sms_quiz_submissions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `sms_quizzes` (`quiz_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_quiz_submissions_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Discussions/Forum
CREATE TABLE `sms_discussions` (
  `discussion_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `content` text NOT NULL,
  `course_id` int(11) DEFAULT NULL,
  `category` enum('general','qna','assignment','announcement','feedback') DEFAULT 'general',
  `pinned` tinyint(1) DEFAULT 0,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`discussion_id`),
  KEY `course_id` (`course_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_discussions_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_discussions_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Discussion replies
CREATE TABLE `sms_discussion_replies` (
  `reply_id` int(11) NOT NULL AUTO_INCREMENT,
  `discussion_id` int(11) NOT NULL,
  `parent_reply_id` int(11) DEFAULT NULL,
  `reply_content` text NOT NULL,
  `replied_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`reply_id`),
  KEY `discussion_id` (`discussion_id`),
  KEY `parent_reply_id` (`parent_reply_id`),
  KEY `replied_by` (`replied_by`),
  CONSTRAINT `sms_discussion_replies_ibfk_1` FOREIGN KEY (`discussion_id`) REFERENCES `sms_discussions` (`discussion_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_discussion_replies_ibfk_2` FOREIGN KEY (`parent_reply_id`) REFERENCES `sms_discussion_replies` (`reply_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_discussion_replies_ibfk_3` FOREIGN KEY (`replied_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Resources/Study Materials
CREATE TABLE `sms_resources` (
  `resource_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `course_id` int(11) DEFAULT NULL,
  `resource_type` enum('document','video','link','image','audio','presentation','other') DEFAULT 'document',
  `file_path` varchar(500) DEFAULT NULL,
  `file_size` varchar(50) DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `external_link` varchar(500) DEFAULT NULL,
  `uploaded_by` int(11) NOT NULL,
  `uploaded_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `download_count` int(11) DEFAULT 0,
  `access_level` enum('public','course_only','private') DEFAULT 'course_only',
  PRIMARY KEY (`resource_id`),
  KEY `course_id` (`course_id`),
  KEY `uploaded_by` (`uploaded_by`),
  CONSTRAINT `sms_resources_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_resources_ibfk_2` FOREIGN KEY (`uploaded_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Resource downloads
CREATE TABLE `sms_resource_downloads` (
  `download_id` int(11) NOT NULL AUTO_INCREMENT,
  `resource_id` int(11) NOT NULL,
  `downloaded_by` int(11) NOT NULL,
  `downloaded_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `ip_address` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`download_id`),
  KEY `resource_id` (`resource_id`),
  KEY `downloaded_by` (`downloaded_by`),
  CONSTRAINT `sms_resource_downloads_ibfk_1` FOREIGN KEY (`resource_id`) REFERENCES `sms_resources` (`resource_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_resource_downloads_ibfk_2` FOREIGN KEY (`downloaded_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Calendar & Events
CREATE TABLE `sms_events` (
  `event_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `event_date` date NOT NULL,
  `event_time` time DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  `end_time` time DEFAULT NULL,
  `event_type` enum('exam','assignment','holiday','meeting','sports','cultural','parent_teacher','other') DEFAULT 'other',
  `course_id` int(11) DEFAULT NULL,
  `class_id` int(10) UNSIGNED DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `color` varchar(20) DEFAULT '#3b82f6',
  `created_by` int(11) NOT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`),
  KEY `course_id` (`course_id`),
  KEY `class_id` (`class_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `sms_events_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_events_ibfk_2` FOREIGN KEY (`class_id`) REFERENCES `sms_classes` (`id`),
  CONSTRAINT `sms_events_ibfk_3` FOREIGN KEY (`created_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notifications
CREATE TABLE `sms_notifications` (
  `notification_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `notification_type` enum('assignment','quiz','announcement','grade','system','attendance','event','message') DEFAULT 'system',
  `reference_id` int(11) DEFAULT NULL,
  `reference_type` varchar(50) DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT 0,
  `read_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`notification_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `sms_notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `sms_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Parent-Student relationships
CREATE TABLE `sms_parent_students` (
  `parent_student_id` int(11) NOT NULL AUTO_INCREMENT,
  `parent_id` int(11) NOT NULL,
  `student_id` int(10) UNSIGNED NOT NULL,
  `relationship` enum('father','mother','guardian','other') DEFAULT 'father',
  `is_primary` tinyint(1) DEFAULT 0,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`parent_student_id`),
  UNIQUE KEY `unique_parent_student` (`parent_id`, `student_id`),
  KEY `parent_id` (`parent_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `sms_parent_students_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `sms_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `sms_parent_students_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Grades/Transcripts
CREATE TABLE `sms_grades` (
  `grade_id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(10) UNSIGNED NOT NULL,
  `course_id` int(11) NOT NULL,
  `assignment_grade` decimal(5,2) DEFAULT NULL,
  `quiz_grade` decimal(5,2) DEFAULT NULL,
  `midterm_grade` decimal(5,2) DEFAULT NULL,
  `final_grade` decimal(5,2) DEFAULT NULL,
  `total_grade` decimal(5,2) DEFAULT NULL,
  `letter_grade` varchar(5) DEFAULT NULL,
  `gpa` decimal(3,2) DEFAULT NULL,
  `academic_year` year NOT NULL,
  `semester` varchar(20) DEFAULT NULL,
  `remarks` text,
  `graded_by` int(11) DEFAULT NULL,
  `graded_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`grade_id`),
  UNIQUE KEY `unique_student_course_grade` (`student_id`, `course_id`, `academic_year`, `semester`),
  KEY `student_id` (`student_id`),
  KEY `course_id` (`course_id`),
  KEY `graded_by` (`graded_by`),
  CONSTRAINT `sms_grades_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `sms_students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `sms_grades_ibfk_2` FOREIGN KEY (`course_id`) REFERENCES `sms_courses` (`course_id`) ON DELETE CASCADE,
  CONSTRAINT `sms_grades_ibfk_3` FOREIGN KEY (`graded_by`) REFERENCES `sms_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Messages/Communications
CREATE TABLE `sms_messages` (
  `message_id` int(11) NOT NULL AUTO_INCREMENT,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `subject` varchar(255) DEFAULT NULL,
  `message` text NOT NULL,
  `message_type` enum('direct','group','announcement') DEFAULT 'direct',
  `group_id` int(11) DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT 0,
  `read_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  KEY `sender_id` (`sender_id`),
  KEY `receiver_id` (`receiver_id`),
  CONSTRAINT `sms_messages_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `sms_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `sms_messages_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `sms_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ==================== INSERT SAMPLE DATA ====================

-- Insert admin user
INSERT INTO `sms_user` (`first_name`, `last_name`, `email`, `password`, `gender`, `mobile`, `designation`, `type`, `status`) VALUES
('Admin', 'User', 'admin@school.com', 'admin123', 'male', '1234567890', 'Administrator', 'administrator', 'active');

SET @admin_id = LAST_INSERT_ID();

-- Insert sections
INSERT INTO `sms_section` (`section`) VALUES
('A'),
('B'),
('C'),
('D');

-- Insert subjects
INSERT INTO `sms_subjects` (`subject`, `type`, `code`, `description`) VALUES
('Mathematics', 'Theory', 101, 'Algebra, Geometry, Calculus'),
('English', 'Theory', 102, 'Grammar, Literature, Composition'),
('Science', 'Theory', 103, 'Physics, Chemistry, Biology'),
('Computer Science', 'Practical', 104, 'Programming, Databases, Networking'),
('History', 'Theory', 105, 'World History, Civics'),
('Physical Education', 'Practical', 106, 'Sports, Fitness, Health');

-- Insert teacher users
INSERT INTO `sms_user` (`first_name`, `last_name`, `email`, `password`, `gender`, `mobile`, `designation`, `type`, `status`) VALUES
('John', 'Smith', 'john.smith@school.com', 'teacher123', 'male', '1112223333', 'Mathematics Teacher', 'teacher', 'active'),
('Sarah', 'Johnson', 'sarah.johnson@school.com', 'teacher123', 'female', '4445556666', 'English Teacher', 'teacher', 'active'),
('Michael', 'Brown', 'michael.brown@school.com', 'teacher123', 'male', '7778889999', 'Science Teacher', 'teacher', 'active'),
('David', 'Wilson', 'david.wilson@school.com', 'teacher123', 'male', '2223334444', 'Computer Science Teacher', 'teacher', 'active');

SET @teacher1_id = LAST_INSERT_ID();
SET @teacher2_id = LAST_INSERT_ID();
SET @teacher3_id = LAST_INSERT_ID();
SET @teacher4_id = LAST_INSERT_ID();

-- Insert teachers
INSERT INTO `sms_teacher` (`teacher`, `subject_id`, `user_id`, `qualification`, `experience`) VALUES
('John Smith', 1, @teacher1_id, 'M.Sc Mathematics', '10 years'),
('Sarah Johnson', 2, @teacher2_id, 'M.A English', '8 years'),
('Michael Brown', 3, @teacher3_id, 'M.Sc Physics', '12 years'),
('David Wilson', 4, @teacher4_id, 'M.Tech Computer Science', '7 years');

-- Insert classes
INSERT INTO `sms_classes` (`name`, `section`, `teacher_id`, `room_number`, `academic_year`) VALUES
('Class 9', 1, 1, 'Room 101', 2024),
('Class 9', 2, 2, 'Room 102', 2024),
('Class 10', 1, 3, 'Room 201', 2024),
('Class 10', 2, 4, 'Room 202', 2024),
('Class 11', 1, 1, 'Room 301', 2024),
('Class 12', 1, 2, 'Room 401', 2024);

-- Insert student users
INSERT INTO `sms_user` (`first_name`, `last_name`, `email`, `password`, `gender`, `mobile`, `type`, `status`) VALUES
('Emma', 'Watson', 'emma.watson@student.com', 'student123', 'female', '1111111111', 'student', 'active'),
('James', 'Miller', 'james.miller@student.com', 'student123', 'male', '2222222222', 'student', 'active'),
('Sophia', 'Davis', 'sophia.davis@student.com', 'student123', 'female', '3333333333', 'student', 'active'),
('William', 'Johnson', 'william.johnson@student.com', 'student123', 'male', '4444444444', 'student', 'active'),
('Olivia', 'Brown', 'olivia.brown@student.com', 'student123', 'female', '5555555555', 'student', 'active'),
('Noah', 'Wilson', 'noah.wilson@student.com', 'student123', 'male', '6666666666', 'student', 'active');

SET @student1_id = LAST_INSERT_ID();
SET @student2_id = LAST_INSERT_ID();
SET @student3_id = LAST_INSERT_ID();
SET @student4_id = LAST_INSERT_ID();
SET @student5_id = LAST_INSERT_ID();
SET @student6_id = LAST_INSERT_ID();

-- Insert students
INSERT INTO `sms_students` (`name`, `gender`, `dob`, `mobile`, `email`, `current_address`, `father_name`, `mother_name`, `admission_no`, `roll_no`, `class`, `section`, `admission_date`, `academic_year`, `user_id`) VALUES
('Emma Watson', 'female', '2007-05-15', '1111111111', 'emma.watson@student.com', '123 Main St, New York', 'Robert Watson', 'Sarah Watson', 'STU2024001', '001', 1, 1, '2024-04-01', 2024, @student1_id),
('James Miller', 'male', '2007-08-22', '2222222222', 'james.miller@student.com', '456 Oak Ave, Chicago', 'Thomas Miller', 'Jennifer Miller', 'STU2024002', '002', 1, 1, '2024-04-01', 2024, @student2_id),
('Sophia Davis', 'female', '2006-03-10', '3333333333', 'sophia.davis@student.com', '789 Pine Rd, Los Angeles', 'David Davis', 'Lisa Davis', 'STU2024003', '003', 2, 2, '2024-04-01', 2024, @student3_id),
('William Johnson', 'male', '2006-11-05', '4444444444', 'william.johnson@student.com', '321 Elm St, Houston', 'John Johnson', 'Mary Johnson', 'STU2024004', '004', 2, 2, '2024-04-01', 2024, @student4_id),
('Olivia Brown', 'female', '2005-09-18', '5555555555', 'olivia.brown@student.com', '654 Maple Dr, Phoenix', 'Charles Brown', 'Patricia Brown', 'STU2024005', '005', 3, 1, '2024-04-01', 2024, @student5_id),
('Noah Wilson', 'male', '2005-12-25', '6666666666', 'noah.wilson@student.com', '987 Cedar Ln, Philadelphia', 'Richard Wilson', 'Nancy Wilson', 'STU2024006', '006', 3, 1, '2024-04-01', 2024, @student6_id);

-- Insert courses
INSERT INTO `sms_courses` (`course_name`, `course_code`, `description`, `teacher_id`, `class_id`, `credit_hours`, `semester`, `status`, `created_by`) VALUES
('Mathematics 101', 'MATH101', 'Basic Algebra and Geometry', 1, 1, 3, 'Spring 2024', 'active', @admin_id),
('English Literature', 'ENG201', 'Introduction to English Literature', 2, 1, 3, 'Spring 2024', 'active', @admin_id),
('Science Fundamentals', 'SCI101', 'Physics, Chemistry and Biology Basics', 3, 2, 4, 'Spring 2024', 'active', @admin_id),
('Computer Programming', 'CSC101', 'Introduction to Python Programming', 4, 2, 4, 'Spring 2024', 'active', @admin_id);

-- Insert course enrollments
INSERT INTO `sms_course_enrollments` (`course_id`, `student_id`, `status`) VALUES
(1, 1, 'active'),
(1, 2, 'active'),
(2, 1, 'active'),
(2, 2, 'active'),
(3, 3, 'active'),
(3, 4, 'active'),
(4, 3, 'active'),
(4, 4, 'active'),
(1, 5, 'active'),
(2, 5, 'active');

-- Insert assignments
INSERT INTO `sms_assignments` (`title`, `description`, `course_id`, `due_date`, `max_marks`, `weightage`, `assignment_type`, `instructions`, `created_by`) VALUES
('Algebra Assignment 1', 'Solve algebraic equations from chapter 1', 1, DATE_ADD(NOW(), INTERVAL 7 DAY), 100, 15, 'individual', 'Show all your work step by step', @teacher1_id),
('Essay Writing', 'Write a 500-word essay on climate change', 2, DATE_ADD(NOW(), INTERVAL 5 DAY), 100, 20, 'individual', 'Use proper formatting and citations', @teacher2_id),
('Science Project', 'Prepare a report on renewable energy sources', 3, DATE_ADD(NOW(), INTERVAL 10 DAY), 100, 25, 'group', 'Include diagrams and references', @teacher3_id);

-- Insert assignment submissions
INSERT INTO `sms_assignment_submissions` (`assignment_id`, `student_id`, `submission_text`, `marks_obtained`, `feedback`, `submission_date`, `status`) VALUES
(1, 1, 'Completed all equations with step-by-step solutions', 85, 'Good work!', NOW(), 'graded'),
(1, 2, 'Submitted assignment with minor errors', 78, 'Check calculation in problem 5', NOW(), 'graded');

-- Insert attendance
INSERT INTO `sms_attendance` (`student_id`, `class_id`, `section_id`, `attendance_status`, `attendance_date`, `recorded_by`) VALUES
(1, 1, 1, 'present', CURDATE(), @admin_id),
(2, 1, 1, 'present', CURDATE(), @admin_id),
(3, 2, 2, 'absent', CURDATE(), @admin_id),
(4, 2, 2, 'present', CURDATE(), @admin_id);

-- Insert announcements
INSERT INTO `sms_announcements` (`title`, `content`, `announcement_type`, `course_id`, `priority`, `created_by`) VALUES
('Welcome to New Academic Year', 'Welcome all students to the 2024 academic year!', 'school', NULL, 'medium', @admin_id),
('Mathematics Class Update', 'Mathematics class tomorrow will be in Room 205 instead of 101', 'course', 1, 'medium', @teacher1_id);

-- Insert events
INSERT INTO `sms_events` (`title`, `description`, `event_date`, `event_type`, `location`, `color`, `created_by`) VALUES
('Mid-Term Exams', 'Mid-term examination week for all classes', DATE_ADD(CURDATE(), INTERVAL 14 DAY), 'exam', 'School Campus', '#ef4444', @admin_id),
('Science Fair', 'Annual science fair competition', DATE_ADD(CURDATE(), INTERVAL 21 DAY), 'cultural', 'School Auditorium', '#10b981', @teacher3_id);

-- ==================== CREATE VIEWS ====================

DROP VIEW IF EXISTS view_student_courses;
DROP VIEW IF EXISTS view_course_students;
DROP VIEW IF EXISTS view_upcoming_deadlines;
DROP VIEW IF EXISTS view_student_attendance_summary;

-- View 1: Student Courses
CREATE VIEW view_student_courses AS
SELECT 
    s.id as student_id,
    s.name as student_name,
    s.admission_no,
    s.roll_no,
    s.email as student_email,
    c.course_id,
    c.course_name,
    c.course_code,
    c.description as course_description,
    c.credit_hours,
    c.semester,
    t.teacher_id,
    t.teacher as teacher_name,
    ce.enrollment_id,
    ce.enrolled_at,
    ce.status as enrollment_status,
    ce.grade as course_grade,
    ce.grade_points,
    ce.completed_at,
    CASE 
        WHEN ce.status = 'active' THEN 'Currently Enrolled'
        WHEN ce.status = 'completed' THEN 'Course Completed'
        WHEN ce.status = 'dropped' THEN 'Dropped Course'
        ELSE 'Pending'
    END as enrollment_status_text
FROM sms_students s
JOIN sms_course_enrollments ce ON s.id = ce.student_id
JOIN sms_courses c ON ce.course_id = c.course_id
JOIN sms_teacher t ON c.teacher_id = t.teacher_id
ORDER BY s.name, ce.enrolled_at DESC;

-- View 2: Course Students
CREATE VIEW view_course_students AS
SELECT 
    c.course_id,
    c.course_name,
    c.course_code,
    t.teacher_id,
    t.teacher as teacher_name,
    s.id as student_id,
    s.name as student_name,
    s.admission_no,
    s.roll_no,
    s.email as student_email,
    cl.name as class_name,
    sec.section,
    ce.enrollment_id,
    ce.enrolled_at,
    ce.status as enrollment_status,
    ce.grade as course_grade,
    DATEDIFF(CURDATE(), ce.enrolled_at) as days_enrolled
FROM sms_courses c
JOIN sms_teacher t ON c.teacher_id = t.teacher_id
JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
JOIN sms_students s ON ce.student_id = s.id
LEFT JOIN sms_classes cl ON s.class = cl.id
LEFT JOIN sms_section sec ON s.section = sec.section_id
WHERE c.status = 'active' AND ce.status = 'active'
ORDER BY c.course_name, s.name;

-- View 3: Upcoming Deadlines
CREATE VIEW view_upcoming_deadlines AS
SELECT 
    'assignment' as item_type,
    a.assignment_id as item_id,
    a.title as item_title,
    c.course_id,
    c.course_name,
    c.course_code,
    t.teacher,
    a.due_date as deadline,
    DATEDIFF(a.due_date, CURDATE()) as days_remaining,
    CASE 
        WHEN DATEDIFF(a.due_date, CURDATE()) = 0 THEN 'Due Today'
        WHEN DATEDIFF(a.due_date, CURDATE()) = 1 THEN 'Due Tomorrow'
        WHEN DATEDIFF(a.due_date, CURDATE()) < 0 THEN 'Overdue'
        WHEN DATEDIFF(a.due_date, CURDATE()) <= 3 THEN 'Due Soon'
        ELSE 'Upcoming'
    END as deadline_status,
    a.max_marks,
    a.created_at
FROM sms_assignments a
JOIN sms_courses c ON a.course_id = c.course_id
JOIN sms_teacher t ON c.teacher_id = t.teacher_id
WHERE a.due_date >= CURDATE()
ORDER BY a.due_date ASC;

-- View 4: Student Attendance Summary
CREATE VIEW view_student_attendance_summary AS
SELECT 
    s.id as student_id,
    s.name as student_name,
    s.admission_no,
    s.roll_no,
    cl.name as class_name,
    sec.section,
    COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) as present_days,
    COUNT(CASE WHEN a.attendance_status = 'absent' THEN 1 END) as absent_days,
    COUNT(CASE WHEN a.attendance_status = 'late' THEN 1 END) as late_days,
    COUNT(*) as total_days,
    ROUND(
        (COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) * 100.0) / 
        NULLIF(COUNT(*), 0), 
    2) as attendance_percentage,
    MAX(a.attendance_date) as last_attendance_date
FROM sms_students s
LEFT JOIN sms_attendance a ON s.id = a.student_id
LEFT JOIN sms_classes cl ON s.class = cl.id
LEFT JOIN sms_section sec ON s.section = sec.section_id
GROUP BY s.id, s.name, s.admission_no, s.roll_no, cl.name, sec.section;

-- ==================== CREATE TRIGGERS ====================

DELIMITER $$

-- Trigger 1: Update attendance cache after insert
DROP TRIGGER IF EXISTS after_attendance_insert$$
CREATE TRIGGER after_attendance_insert
AFTER INSERT ON sms_attendance
FOR EACH ROW
BEGIN
    -- Update notification for student
    INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
    SELECT 
        s.user_id,
        'Attendance Marked',
        CONCAT('Your attendance has been marked as ', NEW.attendance_status, ' for ', NEW.attendance_date),
        'attendance',
        NEW.attendance_id
    FROM sms_students s
    WHERE s.id = NEW.student_id AND s.user_id IS NOT NULL;
    
    -- Update notification for parent
    INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
    SELECT 
        ps.parent_id,
        'Student Attendance Update',
        CONCAT(s.name, '''s attendance marked as ', NEW.attendance_status, ' for ', NEW.attendance_date),
        'attendance',
        NEW.attendance_id
    FROM sms_students s
    JOIN sms_parent_students ps ON s.id = ps.student_id
    WHERE s.id = NEW.student_id;
END$$

-- Trigger 2: Send notification when assignment is created
DROP TRIGGER IF EXISTS after_assignment_create$$
CREATE TRIGGER after_assignment_create
AFTER INSERT ON sms_assignments
FOR EACH ROW
BEGIN
    INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
    SELECT 
        s.user_id,
        'New Assignment',
        CONCAT('New assignment "', NEW.title, '" has been posted in ', c.course_name),
        'assignment',
        NEW.assignment_id
    FROM sms_course_enrollments ce
    JOIN sms_students s ON ce.student_id = s.id
    JOIN sms_courses c ON ce.course_id = c.course_id
    WHERE ce.course_id = NEW.course_id 
        AND ce.status = 'active'
        AND s.user_id IS NOT NULL;
END$$

-- Trigger 3: Send notification when assignment is graded
DROP TRIGGER IF EXISTS after_assignment_graded$$
CREATE TRIGGER after_assignment_graded
AFTER UPDATE ON sms_assignment_submissions
FOR EACH ROW
BEGIN
    IF OLD.marks_obtained IS NULL AND NEW.marks_obtained IS NOT NULL THEN
        INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
        SELECT 
            s.user_id,
            'Assignment Graded',
            CONCAT('Your assignment "', a.title, '" has been graded. Marks: ', NEW.marks_obtained, '/', a.max_marks),
            'grade',
            NEW.submission_id
        FROM sms_assignments a
        JOIN sms_students s ON NEW.student_id = s.id
        WHERE a.assignment_id = NEW.assignment_id
            AND s.user_id IS NOT NULL;
    END IF;
END$$

-- Trigger 4: Send notification when announcement is created
DROP TRIGGER IF EXISTS after_announcement_create$$
CREATE TRIGGER after_announcement_create
AFTER INSERT ON sms_announcements
FOR EACH ROW
BEGIN
    IF NEW.announcement_type = 'school' THEN
        -- Notify all active users
        INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
        SELECT 
            id,
            'School Announcement',
            NEW.title,
            'announcement',
            NEW.announcement_id
        FROM sms_user 
        WHERE status = 'active' AND type IN ('student', 'teacher', 'parent');
    
    ELSEIF NEW.announcement_type = 'course' AND NEW.course_id IS NOT NULL THEN
        -- Notify enrolled students
        INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
        SELECT 
            s.user_id,
            'Course Announcement',
            CONCAT(NEW.title, ' - ', c.course_name),
            'announcement',
            NEW.announcement_id
        FROM sms_course_enrollments ce
        JOIN sms_students s ON ce.student_id = s.id
        JOIN sms_courses c ON ce.course_id = c.course_id
        WHERE ce.course_id = NEW.course_id 
            AND ce.status = 'active'
            AND s.user_id IS NOT NULL;
    END IF;
END$$

-- Trigger 5: Update enrollment status when course is completed
DROP TRIGGER IF EXISTS before_course_enrollment_update$$
CREATE TRIGGER before_course_enrollment_update
BEFORE UPDATE ON sms_course_enrollments
FOR EACH ROW
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        SET NEW.completed_at = NOW();
        
        -- Calculate final grade if not set
        IF NEW.grade IS NULL THEN
            SET NEW.grade = CASE 
                WHEN NEW.grade_points >= 4.0 THEN 'A'
                WHEN NEW.grade_points >= 3.7 THEN 'A-'
                WHEN NEW.grade_points >= 3.3 THEN 'B+'
                WHEN NEW.grade_points >= 3.0 THEN 'B'
                WHEN NEW.grade_points >= 2.7 THEN 'B-'
                WHEN NEW.grade_points >= 2.3 THEN 'C+'
                WHEN NEW.grade_points >= 2.0 THEN 'C'
                WHEN NEW.grade_points >= 1.7 THEN 'C-'
                WHEN NEW.grade_points >= 1.3 THEN 'D+'
                WHEN NEW.grade_points >= 1.0 THEN 'D'
                ELSE 'F'
            END;
        END IF;
    END IF;
END$$

-- Trigger 6: Create notification for new message
DROP TRIGGER IF EXISTS after_message_insert$$
CREATE TRIGGER after_message_insert
AFTER INSERT ON sms_messages
FOR EACH ROW
BEGIN
    INSERT INTO sms_notifications (user_id, title, message, notification_type, reference_id)
    VALUES (
        NEW.receiver_id,
        'New Message',
        CONCAT('New message from ', (SELECT CONCAT(first_name, ' ', last_name) FROM sms_user WHERE id = NEW.sender_id)),
        'message',
        NEW.message_id
    );
END$$

-- Trigger 7: Update resource download count
DROP TRIGGER IF EXISTS after_resource_download$$
CREATE TRIGGER after_resource_download
AFTER INSERT ON sms_resource_downloads
FOR EACH ROW
BEGIN
    UPDATE sms_resources 
    SET download_count = download_count + 1 
    WHERE resource_id = NEW.resource_id;
END$$

-- Trigger 8: Validate student email uniqueness
DROP TRIGGER IF EXISTS before_student_insert$$
CREATE TRIGGER before_student_insert
BEFORE INSERT ON sms_students
FOR EACH ROW
BEGIN
    IF NEW.email IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM sms_students WHERE email = NEW.email AND id != NEW.id) THEN
            SIGNAL SQLSTATE '45000' 
            SET MESSAGE_TEXT = 'Email already exists for another student';
        END IF;
    END IF;
END$$

DELIMITER ;

-- ==================== CREATE STORED PROCEDURES ====================

DELIMITER $$

-- Procedure 1: Get student dashboard data
DROP PROCEDURE IF EXISTS GetStudentDashboardData$$
CREATE PROCEDURE GetStudentDashboardData(IN p_student_id INT)
BEGIN
    -- Student info
    SELECT * FROM sms_students WHERE id = p_student_id;
    
    -- Enrolled courses
    SELECT c.*, t.teacher, ce.enrolled_at, ce.status as enrollment_status
    FROM sms_courses c
    JOIN sms_course_enrollments ce ON c.course_id = ce.course_id
    JOIN sms_teacher t ON c.teacher_id = t.teacher_id
    WHERE ce.student_id = p_student_id AND ce.status = 'active';
    
    -- Upcoming assignments
    SELECT a.*, c.course_name, DATEDIFF(a.due_date, CURDATE()) as days_left
    FROM sms_assignments a
    JOIN sms_courses c ON a.course_id = c.course_id
    WHERE c.course_id IN (
        SELECT course_id FROM sms_course_enrollments 
        WHERE student_id = p_student_id AND status = 'active'
    ) AND a.due_date >= CURDATE()
    ORDER BY a.due_date ASC
    LIMIT 5;
    
    -- Recent announcements
    SELECT a.*, c.course_name 
    FROM sms_announcements a
    LEFT JOIN sms_courses c ON a.course_id = c.course_id
    WHERE (a.course_id IN (
        SELECT course_id FROM sms_course_enrollments 
        WHERE student_id = p_student_id
    ) OR a.announcement_type = 'school')
    ORDER BY a.created_at DESC
    LIMIT 5;
    
    -- Attendance summary
    SELECT 
        COUNT(CASE WHEN attendance_status = 'present' THEN 1 END) as present_days,
        COUNT(CASE WHEN attendance_status = 'absent' THEN 1 END) as absent_days,
        COUNT(*) as total_days,
        ROUND((COUNT(CASE WHEN attendance_status = 'present' THEN 1 END) * 100.0) / NULLIF(COUNT(*), 0), 2) as attendance_percentage
    FROM sms_attendance 
    WHERE student_id = p_student_id;
END$$

-- Procedure 2: Get teacher dashboard data
DROP PROCEDURE IF EXISTS GetTeacherDashboardData$$
CREATE PROCEDURE GetTeacherDashboardData(IN p_teacher_id INT)
BEGIN
    -- Teacher info
    SELECT t.*, u.email, u.mobile 
    FROM sms_teacher t
    LEFT JOIN sms_user u ON t.user_id = u.id
    WHERE t.teacher_id = p_teacher_id;
    
    -- Courses taught
    SELECT c.*, COUNT(DISTINCT ce.student_id) as enrolled_students
    FROM sms_courses c
    LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id AND ce.status = 'active'
    WHERE c.teacher_id = p_teacher_id AND c.status = 'active'
    GROUP BY c.course_id;
    
    -- Assignments to grade
    SELECT a.*, c.course_name, 
           COUNT(DISTINCT s.submission_id) as submissions_received,
           COUNT(DISTINCT ce.student_id) as total_students,
           (COUNT(DISTINCT ce.student_id) - COUNT(DISTINCT s.submission_id)) as submissions_pending
    FROM sms_assignments a
    JOIN sms_courses c ON a.course_id = c.course_id
    LEFT JOIN sms_course_enrollments ce ON c.course_id = ce.course_id AND ce.status = 'active'
    LEFT JOIN sms_assignment_submissions s ON a.assignment_id = s.assignment_id
    WHERE c.teacher_id = p_teacher_id 
        AND a.due_date <= CURDATE()
        AND (s.marks_obtained IS NULL OR s.marks_obtained = 0)
    GROUP BY a.assignment_id
    HAVING submissions_pending > 0
    ORDER BY a.due_date ASC;
    
    -- Today's online classes
    SELECT oc.*, c.course_name 
    FROM sms_online_classes oc
    JOIN sms_courses c ON oc.course_id = c.course_id
    WHERE c.teacher_id = p_teacher_id 
        AND DATE(oc.schedule_time) = CURDATE()
    ORDER BY oc.schedule_time ASC;
END$$

-- Procedure 3: Calculate student GPA
DROP PROCEDURE IF EXISTS CalculateStudentGPA$$
CREATE PROCEDURE CalculateStudentGPA(IN p_student_id INT, IN p_academic_year YEAR)
BEGIN
    SELECT 
        s.name as student_name,
        COUNT(DISTINCT g.course_id) as total_courses,
        ROUND(AVG(g.gpa), 2) as average_gpa,
        SUM(CASE 
            WHEN g.letter_grade = 'A' THEN 4.0
            WHEN g.letter_grade = 'A-' THEN 3.7
            WHEN g.letter_grade = 'B+' THEN 3.3
            WHEN g.letter_grade = 'B' THEN 3.0
            WHEN g.letter_grade = 'B-' THEN 2.7
            WHEN g.letter_grade = 'C+' THEN 2.3
            WHEN g.letter_grade = 'C' THEN 2.0
            WHEN g.letter_grade = 'C-' THEN 1.7
            WHEN g.letter_grade = 'D+' THEN 1.3
            WHEN g.letter_grade = 'D' THEN 1.0
            ELSE 0.0
        END * c.credit_hours) / SUM(c.credit_hours) as weighted_gpa
    FROM sms_students s
    LEFT JOIN sms_grades g ON s.id = g.student_id
    LEFT JOIN sms_courses c ON g.course_id = c.course_id
    WHERE s.id = p_student_id 
        AND g.academic_year = p_academic_year
    GROUP BY s.id, s.name;
END$$

-- Procedure 4: Get attendance report
DROP PROCEDURE IF EXISTS GetAttendanceReport$$
CREATE PROCEDURE GetAttendanceReport(
    IN p_class_id INT,
    IN p_start_date DATE,
    IN p_end_date DATE
)
BEGIN
    SELECT 
        s.id as student_id,
        s.name as student_name,
        s.roll_no,
        s.admission_no,
        COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) as present_days,
        COUNT(CASE WHEN a.attendance_status = 'absent' THEN 1 END) as absent_days,
        COUNT(CASE WHEN a.attendance_status = 'late' THEN 1 END) as late_days,
        COUNT(*) as total_days,
        ROUND((COUNT(CASE WHEN a.attendance_status = 'present' THEN 1 END) * 100.0) / NULLIF(COUNT(*), 0), 2) as attendance_percentage
    FROM sms_students s
    LEFT JOIN sms_attendance a ON s.id = a.student_id 
        AND a.attendance_date BETWEEN p_start_date AND p_end_date
    WHERE s.class = p_class_id
    GROUP BY s.id, s.name, s.roll_no, s.admission_no
    ORDER BY s.roll_no;
END$$

-- Procedure 5: Mark attendance for entire class
DROP PROCEDURE IF EXISTS MarkClassAttendance$$
CREATE PROCEDURE MarkClassAttendance(
    IN p_class_id INT,
    IN p_section_id INT,
    IN p_attendance_date DATE,
    IN p_recorded_by INT
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE student_id INT;
    DECLARE cur CURSOR FOR 
        SELECT id FROM sms_students 
        WHERE class = p_class_id AND section = p_section_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    
    read_loop: LOOP
        FETCH cur INTO student_id;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        -- Insert attendance record (default to 'present')
        INSERT INTO sms_attendance (student_id, class_id, section_id, attendance_status, attendance_date, recorded_by)
        VALUES (student_id, p_class_id, p_section_id, 'present', p_attendance_date, p_recorded_by)
        ON DUPLICATE KEY UPDATE 
            attendance_status = 'present',
            recorded_by = p_recorded_by;
    END LOOP;
    
    CLOSE cur;
    
    SELECT 'Attendance marked successfully' as message;
END$$

DELIMITER ;

-- ==================== CREATE INDEXES ====================

CREATE INDEX idx_student_email ON sms_students(email);
CREATE INDEX idx_student_class ON sms_students(class, section);
CREATE INDEX idx_attendance_date ON sms_attendance(attendance_date);
CREATE INDEX idx_attendance_student ON sms_attendance(student_id, attendance_date);
CREATE INDEX idx_course_enrollment ON sms_course_enrollments(student_id, course_id);
CREATE INDEX idx_assignment_submission ON sms_assignment_submissions(student_id, assignment_id);
CREATE INDEX idx_user_email ON sms_user(email);
CREATE INDEX idx_user_type ON sms_user(type, status);
CREATE INDEX idx_notification_user ON sms_notifications(user_id, is_read, created_at);
CREATE INDEX idx_event_date ON sms_events(event_date, event_type);
CREATE INDEX idx_assignment_due ON sms_assignments(due_date, course_id);
CREATE INDEX idx_quiz_course ON sms_quizzes(course_id, start_date, end_date);

-- ==================== FINAL SETUP ====================

-- Create a cache table for attendance statistics
CREATE TABLE IF NOT EXISTS sms_attendance_cache (
    cache_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT(10) UNSIGNED NOT NULL,
    month_year VARCHAR(7) NOT NULL,
    present_days INT DEFAULT 0,
    absent_days INT DEFAULT 0,
    late_days INT DEFAULT 0,
    total_days INT DEFAULT 0,
    percentage DECIMAL(5,2) DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_student_month (student_id, month_year),
    FOREIGN KEY (student_id) REFERENCES sms_students(id) ON DELETE CASCADE
);

-- Update trigger to maintain cache
DELIMITER $$

DROP TRIGGER IF EXISTS after_attendance_insert_cache$$
CREATE TRIGGER after_attendance_insert_cache
AFTER INSERT ON sms_attendance
FOR EACH ROW
BEGIN
    DECLARE v_month_year VARCHAR(7);
    SET v_month_year = DATE_FORMAT(NEW.attendance_date, '%Y-%m');
    
    INSERT INTO sms_attendance_cache (student_id, month_year, present_days, absent_days, late_days, total_days, percentage)
    VALUES (
        NEW.student_id,
        v_month_year,
        CASE WHEN NEW.attendance_status = 'present' THEN 1 ELSE 0 END,
        CASE WHEN NEW.attendance_status = 'absent' THEN 1 ELSE 0 END,
        CASE WHEN NEW.attendance_status = 'late' THEN 1 ELSE 0 END,
        1,
        CASE WHEN NEW.attendance_status = 'present' THEN 100.00 ELSE 0.00 END
    )
    ON DUPLICATE KEY UPDATE
        present_days = present_days + CASE WHEN NEW.attendance_status = 'present' THEN 1 ELSE 0 END,
        absent_days = absent_days + CASE WHEN NEW.attendance_status = 'absent' THEN 1 ELSE 0 END,
        late_days = late_days + CASE WHEN NEW.attendance_status = 'late' THEN 1 ELSE 0 END,
        total_days = total_days + 1,
        percentage = ROUND(((present_days + CASE WHEN NEW.attendance_status = 'present' THEN 1 ELSE 0 END) * 100.0) / (total_days + 1), 2);
END$$

DELIMITER ;

-- ==================== TEST DATA VERIFICATION ====================

SELECT 'Database Setup Complete' as message;
SELECT 'Sample Users Created:' as info;
SELECT type, COUNT(*) as count FROM sms_user GROUP BY type;

SELECT 'Sample Data Summary:' as info;
SELECT 'Students' as table_name, COUNT(*) as count FROM sms_students
UNION ALL
SELECT 'Teachers', COUNT(*) FROM sms_teacher
UNION ALL
SELECT 'Courses', COUNT(*) FROM sms_courses
UNION ALL
SELECT 'Enrollments', COUNT(*) FROM sms_course_enrollments
UNION ALL
SELECT 'Assignments', COUNT(*) FROM sms_assignments;

-- Show login credentials
SELECT 'Login Credentials:' as info;
SELECT 
    'Admin' as role,
    'admin@school.com' as email,
    'admin123' as password
UNION ALL
SELECT 
    'Teacher (John Smith)',
    'john.smith@school.com',
    'teacher123'
UNION ALL
SELECT 
    'Student (Emma Watson)',
    'emma.watson@student.com',
    'student123';

-- Test views
SELECT 'Testing Views:' as info;
SELECT COUNT(*) as student_courses_count FROM view_student_courses;
SELECT COUNT(*) as course_students_count FROM view_course_students;
SELECT COUNT(*) as upcoming_deadlines_count FROM view_upcoming_deadlines;
SELECT COUNT(*) as attendance_summary_count FROM view_student_attendance_summary;


ALTER TABLE sms_user ADD COLUMN last_login TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE sms_messages ADD COLUMN content TEXT;

CREATE TABLE IF NOT EXISTS sms_calendar_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    course_id INT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type ENUM('assignment', 'exam', 'holiday', 'meeting', 'deadline', 'other') NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME NULL,
    priority ENUM('low', 'medium', 'high') DEFAULT 'medium',
    repeat_weekly BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE sms_calendar_events ADD FOREIGN KEY (user_id) REFERENCES sms_user(id);
ALTER TABLE sms_calendar_events ADD FOREIGN KEY (course_id) REFERENCES sms_courses(course_id);

CREATE TABLE IF NOT EXISTS sms_student_courses ( id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL, 
    course_id INT NOT NULL, 
    enrolled_at TIMESTAMP DEFAULT 
    CURRENT_TIMESTAMP, 
    FOREIGN KEY (student_id) REFERENCES sms_user(id), 
    FOREIGN KEY (course_id) REFERENCES sms_courses(course_id), 
    UNIQUE KEY unique_student_course (student_id, course_id) ); 