# Stage 1: Build the application
FROM eclipse-temurin:21-jdk-jammy AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the Maven wrapper files and pom.xml
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .

# Make mvnw executable
RUN chmod +x mvnw

# Download dependencies (to leverage Docker layer caching)
RUN ./mvnw dependency:go-offline

# Copy the rest of the source code
COPY src ./src

# Build the Spring Boot application
RUN ./mvnw package -DskipTests

# Stage 2: Create the final production image
FROM eclipse-temurin:21-jre-jammy

# Set argument for the JAR file name
ARG JAR_FILE=target/*.jar

# Copy the built JAR from the build stage
COPY --from=build /app/${JAR_FILE} app.jar

# Expose the port your Spring Boot application runs on (default 8080)
EXPOSE 8080

# Run the Spring Boot application
ENTRYPOINT ["java","-jar","/app.jar"]